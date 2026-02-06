"""RAG index: add/update/delete documents and upload JSONL."""

import asyncio
import json
import time

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas.requests import UpdateAgentIndexRequest
from app.schemas.responses import UpdateAgentIndexResponse, UploadAndIndexResponse
from app.services.rag import get_or_create_retriever

router = APIRouter(tags=["RAG Index"])


def _update_agent_index_sync(
    request: UpdateAgentIndexRequest,
) -> UpdateAgentIndexResponse:
    rag = get_or_create_retriever(request.agent_name)
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


def _upload_and_index_sync(agent_name: str, content: bytes) -> UploadAndIndexResponse:
    rag = get_or_create_retriever(agent_name)
    lines = content.decode("utf-8").splitlines()
    docs = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
            if not doc.get("id"):
                doc["id"] = f"upload_{agent_name}_{i}"
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
    agent_name: str = Form(..., description="Agent name"),
    file: UploadFile = File(..., description="JSONL file"),
) -> UploadAndIndexResponse:
    content = await file.read()
    return await asyncio.to_thread(_upload_and_index_sync, agent_name, content)
