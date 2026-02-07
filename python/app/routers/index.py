"""RAG index: add/update/delete documents, upload JSONL, ingest PDF/TXT/DOCX."""

import asyncio
import json
import time
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from google.api_core.exceptions import FailedPrecondition

from app.schemas.requests import UpdateAgentIndexRequest
from app.schemas.responses import UpdateAgentIndexResponse, UploadAndIndexResponse
from app.services.document_parser import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES,
    file_to_docs,
)
from app.services.file_storage import upload as gcs_upload
from app.services.rag import get_or_create_retriever

_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

router = APIRouter(tags=["RAG Index"])


def _update_agent_index_sync(
    request: UpdateAgentIndexRequest,
) -> UpdateAgentIndexResponse:
    rag = get_or_create_retriever(request.agent_key())
    action = request.action.lower()
    if action in ("add", "update"):
        if not request.content:
            raise HTTPException(status_code=400, detail="content required for add/update")
        doc_data = json.loads(request.content)
        if not doc_data.get("id"):
            doc_data["id"] = f"doc_{int(time.time())}"
        if request.metadata is not None:
            doc_data["metadata"] = request.metadata
        rag.add_or_update_documents([doc_data])
    elif action == "delete":
        if not request.doc_id:
            raise HTTPException(status_code=400, detail="doc_id required for delete")
        if not rag.delete_document(request.doc_id):
            raise HTTPException(status_code=404, detail="Document not found")
    else:
        raise HTTPException(status_code=400, detail="action must be add, update, or delete")
    return UpdateAgentIndexResponse(status="success", total_docs=rag.count_documents())


@router.post(
    "/update_agent_index",
    response_model=UpdateAgentIndexResponse,
    summary="Update agent RAG index",
    description="Add, update, or delete a document in the agent's LanceDB index. "
    "Actions: 'add' | 'update' (require content JSON with id, content, optional metadata), 'delete' (require doc_id).",
    operation_id="updateAgentIndex",
)
async def update_agent_index(
    request: UpdateAgentIndexRequest,
) -> UpdateAgentIndexResponse:
    return await asyncio.to_thread(_update_agent_index_sync, request)


def _upload_and_index_sync(agent_key: str, content: bytes) -> UploadAndIndexResponse:
    rag = get_or_create_retriever(agent_key)
    lines = content.decode("utf-8").splitlines()
    docs = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
            if not doc.get("id"):
                doc["id"] = f"upload_{agent_key}_{i}"
            docs.append(doc)
        except json.JSONDecodeError:
            continue
    if docs:
        rag.add_or_update_documents(docs)
    return UploadAndIndexResponse(
        status="success",
        docs_added=len(docs),
        total_docs=rag.count_documents(),
    )


@router.post(
    "/upload_and_index",
    response_model=UploadAndIndexResponse,
    summary="Upload JSONL and index",
    description="Upload a JSONL file (one JSON object per line with id, content, optional metadata) and index into the agent's RAG.",
    operation_id="uploadAndIndex",
)
async def upload_and_index(
    agent_id: str | None = Form(None, description="Agent ID (UUID from app API)"),
    agent_name: str | None = Form(None, description="Agent name (legacy)"),
    file: UploadFile = File(..., description="JSONL file"),
) -> UploadAndIndexResponse:
    agent_key = (agent_id or agent_name or "").strip()
    if not agent_key:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of agent_id or agent_name",
        )
    content = await file.read()
    return await asyncio.to_thread(_upload_and_index_sync, agent_key, content)


def _ingest_document_sync(agent_key: str, content: bytes, filename: str) -> UploadAndIndexResponse:
    """Upload raw file to GCS, then convert to text, chunk, and index. Embeddings created by RAG."""
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)",
        )
    path = Path(filename)
    ext = path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    content_type = _CONTENT_TYPES.get(ext, "application/octet-stream")
    source_id = f"ingest_{path.stem}_{int(time.time())}"
    file_key = f"{source_id}{ext}"
    try:
        source_gcs_uri = gcs_upload(agent_key, file_key, content, content_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}") from e
    try:
        docs = file_to_docs(content, filename, source_file_uri=source_gcs_uri)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not docs:
        return UploadAndIndexResponse(
            status="success",
            docs_added=0,
            total_docs=get_or_create_retriever(agent_key).count_documents(),
        )
    rag = get_or_create_retriever(agent_key)
    try:
        rag.add_or_update_documents(docs)
    except FailedPrecondition as e:
        if "StreamUpdate is not enabled" in str(e):
            raise HTTPException(
                status_code=400,
                detail="Your Vector Search index uses Batch updates. This app requires a Streaming index. "
                "In Vertex AI Vector Search, create a new index with Update method: Streaming (768 dimensions), "
                "deploy it to an endpoint, and set VERTEX_RAG_INDEX_ID, VERTEX_RAG_INDEX_ENDPOINT_ID, "
                "VERTEX_RAG_DEPLOYED_INDEX_ID to the new index. See python/scripts/create_vertex_index.py.",
            ) from e
        raise HTTPException(status_code=500, detail=str(e)) from e
    return UploadAndIndexResponse(
        status="success",
        docs_added=len(docs),
        total_docs=rag.count_documents(),
    )


@router.post(
    "/ingest_document",
    response_model=UploadAndIndexResponse,
    summary="Ingest document (PDF, TXT, DOCX)",
    description="Upload a PDF, TXT, or DOCX file. Content is extracted to text, chunked, "
    "embedded automatically, and added to the agent's RAG index.",
    operation_id="ingestDocument",
)
async def ingest_document(
    agent_id: str | None = Form(None, description="Agent ID (UUID from app API)"),
    agent_name: str | None = Form(None, description="Agent name (legacy)"),
    file: UploadFile = File(..., description="PDF, TXT, or DOCX file"),
) -> UploadAndIndexResponse:
    agent_key = (agent_id or agent_name or "").strip()
    if not agent_key:
        raise HTTPException(
            status_code=400,
            detail="Provide exactly one of agent_id or agent_name",
        )
    content = await file.read()
    return await asyncio.to_thread(
        _ingest_document_sync,
        agent_key,
        content,
        file.filename or "document",
    )
