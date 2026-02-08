"""Agent documents: list, get, delete, and record ingested docs (DB + RAG sync). No content in DB; RAG owns chunks."""

import uuid

from app.db import session_scope
from app.models import AgentDocument
from app.services.document_parser import file_to_docs
from app.services.file_storage import generate_signed_url
from app.services.file_storage import upload as gcs_upload
from app.services.rag import get_or_create_retriever


def list_documents(
    agent_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[AgentDocument], int]:
    """List documents for an agent (paginated). Returns (items, total)."""
    offset = (page - 1) * limit
    with session_scope() as session:
        q = session.query(AgentDocument).filter(AgentDocument.agent_id == agent_id)
        total = q.count()
        items = q.order_by(AgentDocument.created_at.desc()).offset(offset).limit(limit).all()
        return list(items), total


def document_to_response(doc: AgentDocument, signed_url_expiry_seconds: int = 3600) -> dict:
    """Build API response dict for one document. Includes authenticated downloadUrl when storage_path is set."""
    download_url = (
        generate_signed_url(doc.storage_path or "", expiration_seconds=signed_url_expiry_seconds)
        if doc.storage_path
        else None
    )
    return {
        "id": str(doc.id),
        "name": doc.name,
        "sourceFilename": doc.source_filename,
        "downloadUrl": download_url,
        "createdAt": doc.created_at.isoformat(),
    }


def _doc_rag_ids(doc: AgentDocument) -> list[str]:
    """All RAG document IDs for this record (one per file or legacy one per chunk)."""
    if doc.rag_document_ids:
        return list(doc.rag_document_ids)
    return [doc.document_id]


def get_document(agent_id: uuid.UUID, document_id: str) -> AgentDocument | None:
    """Get a document by id (UUID) or by RAG document_id. Returns None if not found."""
    with session_scope() as session:
        # Try as our UUID first
        try:
            doc_uuid = uuid.UUID(document_id)
            doc = (
                session.query(AgentDocument)
                .filter(AgentDocument.agent_id == agent_id, AgentDocument.id == doc_uuid)
                .first()
            )
            if doc:
                return doc
        except ValueError:
            pass
        # Else match document_id column or any id in rag_document_ids
        rows = session.query(AgentDocument).filter(AgentDocument.agent_id == agent_id).all()
        for doc in rows:
            if doc.document_id == document_id:
                return doc
            if doc.rag_document_ids and document_id in doc.rag_document_ids:
                return doc
        return None


def delete_document(agent_id: uuid.UUID, document_id: str) -> bool:
    """Delete document by our id (UUID) or RAG document_id. Removes all RAG chunks for that file and DB row."""
    doc = get_document(agent_id, document_id)
    if not doc:
        return False
    rag = get_or_create_retriever(str(agent_id))
    for rag_id in _doc_rag_ids(doc):
        rag.delete_document(rag_id)
    with session_scope() as session:
        session.query(AgentDocument).filter(
            AgentDocument.agent_id == agent_id,
            AgentDocument.id == doc.id,
        ).delete(synchronize_session=False)
    return True


def ingest_one_file_sync(
    agent_id: uuid.UUID,
    filename: str,
    content: bytes,
) -> int:
    """
    Upload file to GCS, chunk and add to RAG, record one row in DB (no content stored).
    Returns number of RAG chunks added.
    """
    doc_id = uuid.uuid4()
    content_type = "application/octet-stream"
    if filename.lower().endswith(".pdf"):
        content_type = "application/pdf"
    elif filename.lower().endswith(".txt"):
        content_type = "text/plain"
    elif filename.lower().endswith(".docx"):
        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    storage_path = gcs_upload(str(agent_id), f"{doc_id}/{filename}", content, content_type)
    docs = file_to_docs(content, filename, storage_path)
    if not docs:
        return 0
    rag = get_or_create_retriever(str(agent_id))
    rag.add_or_update_documents(docs)
    record_documents(agent_id, docs, source_name=filename, storage_path=storage_path, document_id=doc_id)
    return len(docs)


def record_documents(
    agent_id: uuid.UUID,
    docs: list[dict],
    source_name: str = "",
    storage_path: str | None = None,
    document_id: uuid.UUID | None = None,
) -> uuid.UUID | None:
    """
    Insert one agent_documents row per file (after GCS upload and RAG add).
    Returns the created row's id. document_id is our row id when we created it before upload.
    """
    if not docs:
        return None
    name = (source_name or "document").strip() or "document"
    doc_ids = [d.get("id") or "" for d in docs if d.get("id")]
    if not doc_ids:
        return None
    with session_scope() as session:
        rec = AgentDocument(
            id=document_id or uuid.uuid4(),
            agent_id=agent_id,
            document_id=doc_ids[0],
            rag_document_ids=doc_ids,
            name=name,
            source_filename=source_name or None,
            storage_path=storage_path or None,
        )
        session.add(rec)
        return rec.id
