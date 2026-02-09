"""Agent CRUD and prompt optimization. DB is source of truth when configured."""

import asyncio
import base64
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth.db import get_users_by_ids
from app.auth.deps import get_current_user
from app.config import get_settings

logger = logging.getLogger("app.agents")
from app.schemas.requests import CreateAgentRequest, UpdateAgentRequest
from app.schemas.responses import (
    AgentDetailResponse,
    AgentInfo,
    AgentMetadata,
    AgentMode,
    AgentStatusIndexing,
    AgentToolRef,
    ListAgentsResponse,
    PaginationMeta,
    UserRef,
)
from app.services.agent_service import (
    create_agent as create_agent_db,
)
from app.services.agent_service import (
    delete_agent as delete_agent_db,
)
from app.services.agent_service import (
    get_agent,
    get_agent_detail_response,
    list_agents_from_db,
    set_agent_indexing_status,
)
from app.services.agent_service import (
    update_agent as update_agent_db,
)
from app.services.document_parser import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES
from app.services.documents_service import (
    delete_document as delete_document_svc,
)
from app.services.documents_service import (
    document_to_response as document_to_response_svc,
)
from app.services.documents_service import (
    get_document as get_document_svc,
)
from app.services.documents_service import (
    ingest_one_file_sync as ingest_one_file_sync_svc,
)
from app.services.documents_service import (
    list_documents as list_documents_svc,
)
from app.services.documents_service import (
    record_documents as record_documents_svc,
)
from app.services.indexing_queue import enqueue_add_document, enqueue_ingest
from app.services.prompt_queue import enqueue_generate_prompt
from app.services.rag import get_or_create_retriever, list_agents_with_doc_counts

router = APIRouter(tags=["Agents"])

# Document routes under their own tag only (no "Agents" tag)
documents_router = APIRouter(prefix="/agents", tags=["Agents -> Documents"])


def _metadata_from_agent(agent) -> AgentMetadata:
    status_obj = (
        (agent.resolved_metadata.get("status") or {}) if isinstance(agent.resolved_metadata.get("status"), dict) else {}
    )
    indexing = status_obj.get("indexing", "completed")
    enrich = status_obj.get("enrich", "pending")
    return AgentMetadata(status=AgentStatusIndexing(indexing=indexing, enrich=enrich))


def _agent_detail(agent, doc_count: int) -> AgentDetailResponse:
    instructions = [i.content for i in sorted(agent.instructions, key=lambda x: x.order)]
    tools = [AgentToolRef(id=str(at.tool.id), name=at.tool.name) for at in agent.agent_tools]
    return AgentDetailResponse(
        agent_id=str(agent.id),
        user_id=agent.user_id,
        name=agent.name,
        mode=AgentMode(agent.mode),
        prompt=agent.prompt,
        instructions=instructions,
        tools=tools,
        doc_count=doc_count,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        metadata=_metadata_from_agent(agent),
    )


@router.get(
    "/agents",
    response_model=ListAgentsResponse,
    summary="List all agents",
    description="From DB when configured (optionally by user_id), else from RAG registry. Includes RAG doc count.",
    operation_id="listAgents",
)
async def list_agents(
    current_user: dict = Depends(get_current_user),
    user_id: str | None = Query(None, description="Filter by owner"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> ListAgentsResponse:
    settings = get_settings()
    uid = user_id or (current_user["id"] if current_user else None)
    if settings.database_configured:
        items, total = await asyncio.to_thread(list_agents_from_db, uid, page, limit)
        user_ids = list({agent.user_id for agent, _ in items})
        users_map = await asyncio.to_thread(get_users_by_ids, user_ids)
        pages = (total + limit - 1) // limit if total else 0
        return ListAgentsResponse(
            agents=[
                AgentInfo(
                    agent_id=str(agent.id),
                    name=agent.name,
                    mode=AgentMode(agent.mode),
                    prompt=agent.prompt,
                    instructions=[i.content for i in sorted(agent.instructions, key=lambda x: x.order)],
                    user=UserRef(id=u["id"], name=u["name"]) if (u := users_map.get(agent.user_id)) else None,
                    doc_count=doc_count,
                    tools=[AgentToolRef(id=str(at.tool.id), name=at.tool.name) for at in agent.agent_tools],
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                    metadata=_metadata_from_agent(agent),
                )
                for agent, doc_count in items
            ],
            meta=PaginationMeta(page=page, limit=limit, total=total, pages=pages, more=page < pages),
        )
    items = await asyncio.to_thread(list_agents_with_doc_counts)
    default_meta = AgentMetadata(status=AgentStatusIndexing(indexing="completed", enrich="pending"))
    return ListAgentsResponse(
        agents=[
            AgentInfo(agent_id=key, name=key, user=None, doc_count=count, metadata=default_meta) for key, count in items
        ]
    )


@router.post(
    "/agents",
    response_model=AgentDetailResponse,
    summary="Create a new agent",
    description="Create agent in DB (and init RAG). Agent ID is always server-generated.",
    operation_id="createAgent",
)
async def create_agent(
    body: CreateAgentRequest,
    current_user: dict = Depends(get_current_user),
) -> AgentDetailResponse:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured; set DATABASE_URL")
    try:
        agent = await asyncio.to_thread(
            create_agent_db,
            user_id=current_user["id"],
            name=body.name,
            mode=body.mode,
            prompt=body.prompt,
            instructions=body.instructions,
            tools=body.tools,
        )
        if get_settings().queue_configured:
            await enqueue_generate_prompt(agent.id)
        detail = await asyncio.to_thread(get_agent_detail_response, agent.id, current_user["id"])
        return detail
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/agents/{agent_id}",
    response_model=AgentDetailResponse,
    summary="Get agent by ID",
    description="Get agent by id (from DB when configured).",
    operation_id="getAgent",
)
async def get_agent_by_id(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    user_id: str | None = Query(None, description="Require owner"),
) -> AgentDetailResponse:
    settings = get_settings()
    if not settings.database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    uid = user_id or current_user["id"]
    detail = await asyncio.to_thread(get_agent_detail_response, agent_id, uid)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return detail


@router.patch(
    "/agents/{agent_id}",
    response_model=AgentDetailResponse,
    summary="Update agent by ID",
    description="Update name, mode, prompt, instructions, or tools.",
    operation_id="updateAgent",
)
async def update_agent_by_id(
    agent_id: UUID,
    body: UpdateAgentRequest,
    current_user: dict = Depends(get_current_user),
    user_id: str | None = Query(None, description="Require owner"),
) -> AgentDetailResponse:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    uid = user_id or current_user["id"]
    updated = await asyncio.to_thread(
        update_agent_db,
        agent_id,
        user_id=uid,
        name=body.name,
        mode=body.mode,
        prompt=body.prompt,
        instructions=body.instructions,
        tools=body.tools,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    # Re-enqueue prompt enrichment when instructions or tools change (align with create flow)
    if get_settings().queue_configured and (body.instructions is not None or body.tools is not None):
        await enqueue_generate_prompt(agent_id)
    detail = await asyncio.to_thread(get_agent_detail_response, agent_id, uid)
    if detail is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return detail


class DocumentsIngestBody(BaseModel):
    filename: str = ""
    contentBase64: str = ""  # camelCase to match frontend/OpenAPI


@documents_router.post(
    "/{agent_id}/documents/ingest",
    summary="Ingest document for agent RAG",
    description=(
        "Upload a document (base64); content is chunked and added to the agent's RAG index. "
        "When queue is configured, returns 202 with job_id."
    ),
    operation_id="ingestAgentDocument",
)
async def ingest_document(
    agent_id: UUID,
    body: DocumentsIngestBody,
    current_user: dict = Depends(get_current_user),
):
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=current_user["id"], with_relations=False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    filename = (body.filename or "").strip()
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")
    content_b64 = body.contentBase64 or ""
    if not content_b64:
        raise HTTPException(status_code=400, detail="contentBase64 is required")
    ext = "." + filename.split(".")[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    try:
        content = base64.b64decode(content_b64, validate=True)
    except Exception:
        raise HTTPException(status_code=400, detail="contentBase64 is not valid base64")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB)")

    settings = get_settings()
    if settings.queue_configured:
        job_id = await enqueue_ingest(agent_id, filename, content_b64)
        if job_id:
            await asyncio.to_thread(set_agent_indexing_status, agent_id, "pending")
            return JSONResponse(status_code=202, content={"job_id": job_id, "message": "indexing queued"})

    await asyncio.to_thread(set_agent_indexing_status, agent_id, "pending")
    try:
        if not settings.database_configured:
            raise HTTPException(status_code=503, detail="Database required for document ingest")
        count = await asyncio.to_thread(ingest_one_file_sync_svc, agent_id, filename, content)
        await asyncio.to_thread(set_agent_indexing_status, agent_id, "completed")
        return {"documents_added": count, "message": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        await asyncio.to_thread(set_agent_indexing_status, agent_id, "error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@documents_router.get(
    "/{agent_id}/documents",
    summary="List agent documents",
    description="Paginated list of documents in the agent's RAG index (requires database).",
    operation_id="listAgentDocuments",
)
async def list_agent_documents(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured; document list requires DB")
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=current_user["id"], with_relations=False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    items, total = await asyncio.to_thread(list_documents_svc, agent_id, page, limit)
    pages = (total + limit - 1) // limit if total else 0
    return {
        "data": [document_to_response_svc(d) for d in items],
        "meta": {"page": page, "limit": limit, "total": total, "pages": pages, "more": page < pages},
    }


@documents_router.get(
    "/{agent_id}/documents/{document_id}",
    summary="Get document by ID",
    description="Get a single document by id (UUID or RAG document_id).",
    operation_id="getAgentDocument",
)
async def get_agent_document(
    agent_id: UUID,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=current_user["id"], with_relations=False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    doc = await asyncio.to_thread(get_document_svc, agent_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return document_to_response_svc(doc)


class DocumentAddBody(BaseModel):
    """Add a single document to the agent's RAG index."""

    id: str | None = None  # optional; generated if omitted
    content: str = ""
    metadata: dict | None = None


@documents_router.post(
    "/{agent_id}/documents",
    summary="Add document",
    description=(
        "Add a single document by content (and optional id/metadata). "
        "When queue is configured, returns 202 with job_id."
    ),
    operation_id="addAgentDocument",
)
async def add_agent_document(
    agent_id: UUID,
    body: DocumentAddBody,
    current_user: dict = Depends(get_current_user),
):
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=current_user["id"], with_relations=False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    import time

    doc_id = body.id or f"doc_{int(time.time())}_{id(body) % 10000}"
    doc = {"id": doc_id, "content": content, "metadata": body.metadata or {}}
    settings = get_settings()
    if settings.queue_configured:
        job_id = await enqueue_add_document(agent_id, doc)
        if job_id:
            await asyncio.to_thread(set_agent_indexing_status, agent_id, "pending")
            return JSONResponse(status_code=202, content={"job_id": job_id, "message": "indexing queued"})

    await asyncio.to_thread(set_agent_indexing_status, agent_id, "pending")
    try:
        rag = get_or_create_retriever(str(agent_id))
        await asyncio.to_thread(rag.add_or_update_documents, [doc])
        if settings.database_configured:
            await asyncio.to_thread(record_documents_svc, agent_id, [doc], source_name="")
        await asyncio.to_thread(set_agent_indexing_status, agent_id, "completed")
        total_docs = await asyncio.to_thread(rag.count_documents)
        return {
            "id": doc_id,
            "message": "created",
            "total_docs": total_docs,
        }
    except Exception as e:
        await asyncio.to_thread(set_agent_indexing_status, agent_id, "error", str(e))
        raise HTTPException(status_code=500, detail=str(e))


@documents_router.delete(
    "/{agent_id}/documents/{document_id}",
    status_code=204,
    summary="Delete document",
    description="Remove a document from the agent's RAG index and DB.",
    operation_id="deleteAgentDocument",
)
async def delete_agent_document(
    agent_id: UUID,
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=current_user["id"], with_relations=False)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    ok = await asyncio.to_thread(delete_document_svc, agent_id, document_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Document not found")


@router.delete(
    "/agents/{agent_id}",
    status_code=204,
    summary="Delete agent",
    description="Soft delete (default) or hard delete. Requires owner.",
    operation_id="deleteAgent",
)
async def delete_agent_by_id(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    user_id: str | None = Query(None, description="Require owner"),
    soft: bool = Query(True, description="Soft delete (default) or hard delete"),
) -> None:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    uid = user_id or current_user["id"]
    ok = await asyncio.to_thread(delete_agent_db, agent_id, user_id=uid, soft=soft)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
