"""Extract raw text from uploaded documents (PDF, TXT, DOCX, CSV) and optional chunking."""

import csv
import logging
import re
import time
from io import BytesIO, StringIO
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

logger = logging.getLogger(__name__)


def _extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF. Tries PyMuPDF first (more robust), then pypdf with strict=False."""
    # 1. Try PyMuPDF (fitz) – often more robust and lower memory for malformed PDFs
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=content, filetype="pdf")
        try:
            parts = [page.get_text() for page in doc]
            return "\n\n".join(parts) if parts else ""
        finally:
            doc.close()
    except ImportError:
        pass
    except Exception as e:
        logger.warning("PyMuPDF PDF extraction failed, falling back to pypdf: %s", e)

    # 2. Fallback: pypdf with strict=False to tolerate malformed PDFs
    try:
        reader = PdfReader(BytesIO(content), strict=False)
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n\n".join(parts)
    except Exception as e:
        raise ValueError(f"Failed to parse PDF: {e}") from e


def csv_to_text(content: bytes) -> str:
    """Parse CSV to readable text (pipe-separated). Used by RAG and chat attachments."""
    text = content.decode("utf-8", errors="replace")
    reader = csv.reader(StringIO(text))
    rows = list(reader)
    if not rows:
        return ""
    return "\n".join(" | ".join(str(cell) for cell in row) for row in rows)


def _extract_csv_text(content: bytes) -> str:
    """Extract text from CSV for RAG chunking."""
    return csv_to_text(content)


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx", ".csv"}
MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB
CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200


def _chunk_text(
    text: str,
    source_id: str,
    source_file_uri: str | None = None,
) -> list[dict]:
    """Split text into overlapping chunks for RAG. Each chunk becomes one document."""
    if not text or not text.strip():
        return []
    text = text.strip()
    # Split by paragraphs first, then by size
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if current_len + len(para) + 2 <= CHUNK_SIZE_CHARS:
            current.append(para)
            current_len += len(para) + 2
        else:
            if current:
                chunks.append("\n\n".join(current))
            if len(para) > CHUNK_SIZE_CHARS:
                # Split long paragraph by sentences or fixed size
                start = 0
                while start < len(para):
                    end = min(start + CHUNK_SIZE_CHARS, len(para))
                    chunk_slice = para[start:end]
                    if end < len(para):
                        last_period = chunk_slice.rfind(". ")
                        if last_period > CHUNK_SIZE_CHARS // 2:
                            end = start + last_period + 1
                            chunk_slice = para[start:end]
                    chunks.append(chunk_slice)
                    start = end + 1 - CHUNK_OVERLAP_CHARS
                    start = max(0, start)
                current = []
                current_len = 0
            else:
                current = [para]
                current_len = len(para) + 2

    if current:
        chunks.append("\n\n".join(current))

    base_id = re.sub(r"[^\w\-.]", "_", source_id)
    meta_base: dict = {"source": source_id, "chunk_index": 0}
    if source_file_uri:
        meta_base["source_gcs_uri"] = source_file_uri
    return [
        {
            "id": f"{base_id}_chunk_{i}",
            "content": c,
            "metadata": {**meta_base, "chunk_index": i},
        }
        for i, c in enumerate(chunks)
    ]


def extract_text_from_file(content: bytes, filename: str) -> str:
    """Extract raw text from file content. Raises ValueError on unsupported type or parse error."""
    path = Path(filename)
    suffix = path.suffix.lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    if suffix == ".txt":
        return content.decode("utf-8", errors="replace")

    if suffix == ".pdf":
        return _extract_pdf_text(content)

    if suffix == ".docx":
        try:
            doc = DocxDocument(BytesIO(content))
            return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            raise ValueError(f"Failed to parse DOCX: {e}") from e

    if suffix == ".csv":
        return _extract_csv_text(content)

    raise ValueError(f"Unsupported file type: {suffix}")


def file_to_docs(
    content: bytes,
    filename: str,
    source_file_uri: str | None = None,
) -> list[dict]:
    """
    Convert uploaded file to list of RAG documents (with optional chunking).
    Each doc has id, content, metadata. Long documents are chunked.
    If source_file_uri is provided (e.g. gs://...), it is added to each chunk's metadata as source_gcs_uri.
    """
    raw = extract_text_from_file(content, filename)
    if not raw.strip():
        return []
    # Use filename (sanitized) as source id; chunking adds _chunk_N
    source_id = f"ingest_{Path(filename).stem}_{int(time.time())}"
    return _chunk_text(raw, source_id, source_file_uri)
