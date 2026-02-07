"""Agent CRUD and prompt optimization. DB is source of truth when configured."""

import asyncio
import logging
from uuid import UUID

import requests
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings

logger = logging.getLogger("app.agents")
from app.schemas.requests import AgentConfig, CreateAgentRequest, UpdateAgentRequest
from app.schemas.responses import (
    AgentDetailResponse,
    AgentInfo,
    CreateAgentResponse,
    ListAgentsResponse,
    OptimizePromptResponse,
    UpdateAgentGeminimeshResponse,
)
from app.services.agent_service import (
    create_agent as create_agent_db,
    delete_agent as delete_agent_db,
    get_agent,
    list_agents_from_db,
    update_agent as update_agent_db,
)
from app.services.gemini_router import optimize_agent_prompt
from app.services.geminimesh import update_agent_in_geminimesh
from app.services.rag import get_or_create_retriever, list_agents_with_doc_counts

router = APIRouter(tags=["Agents"])


def _agent_detail(agent, doc_count: int) -> AgentDetailResponse:
    instructions = [i.content for i in sorted(agent.instructions, key=lambda x: x.order)]
    tools = [at.tool.name for at in agent.agent_tools]
    return AgentDetailResponse(
        agent_id=str(agent.id),
        user_id=agent.user_id,
        name=agent.name,
        mode=agent.mode,
        prompt=agent.prompt,
        instructions=instructions,
        tools=tools,
        doc_count=doc_count,
    )


@router.get(
    "/agents",
    response_model=ListAgentsResponse,
    summary="List agents",
    description="From DB when configured (optionally by user_id), else from RAG registry. Includes RAG doc count.",
    operation_id="listAgents",
)
async def list_agents(
    user_id: str | None = Query(None, description="Filter by owner (when using DB)"),
) -> ListAgentsResponse:
    settings = get_settings()
    if settings.database_configured:
        items = await asyncio.to_thread(list_agents_from_db, user_id)
        return ListAgentsResponse(
            agents=[
                AgentInfo(
                    agent_id=str(agent.id),
                    name=agent.name,
                    doc_count=doc_count,
                    user_id=agent.user_id,
                )
                for agent, doc_count in items
            ]
        )
    items = await asyncio.to_thread(list_agents_with_doc_counts)
    return ListAgentsResponse(
        agents=[AgentInfo(agent_id=key, name=key, doc_count=count, user_id=None) for key, count in items]
    )


@router.post(
    "/agents",
    response_model=CreateAgentResponse,
    summary="Create agent",
    description="Create agent in DB (and init RAG). Pass agent_id to use a specific UUID (e.g. from Node).",
    operation_id="createAgent",
)
async def create_agent(body: CreateAgentRequest) -> CreateAgentResponse:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured; set DATABASE_URL")
    try:
        agent = await asyncio.to_thread(
            create_agent_db,
            user_id=body.user_id,
            name=body.name,
            mode=body.mode,
            prompt=body.prompt,
            instructions=body.instructions,
            tools=body.tools,
            agent_id=body.agent_id,
        )
        return CreateAgentResponse(agent_id=str(agent.id), message="created")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/agents/{agent_id}",
    response_model=AgentDetailResponse,
    summary="Get agent",
    description="Get agent by id (from DB when configured).",
    operation_id="getAgent",
)
async def get_agent_by_id(
    agent_id: UUID,
    user_id: str | None = Query(None, description="Require owner (when using DB)"),
) -> AgentDetailResponse:
    settings = get_settings()
    if not settings.database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    agent = await asyncio.to_thread(get_agent, agent_id, user_id=user_id, with_relations=True)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    from app.services.agent_service import _rag_doc_count

    doc_count = await asyncio.to_thread(_rag_doc_count, str(agent.id))
    return _agent_detail(agent, doc_count)


@router.patch(
    "/agents/{agent_id}",
    response_model=AgentDetailResponse,
    summary="Update agent",
    operation_id="updateAgent",
)
async def update_agent_by_id(
    agent_id: UUID,
    body: UpdateAgentRequest,
    user_id: str | None = Query(None, description="Require owner"),
) -> AgentDetailResponse:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    agent = await asyncio.to_thread(
        update_agent_db,
        agent_id,
        user_id=user_id,
        name=body.name,
        mode=body.mode,
        prompt=body.prompt,
        instructions=body.instructions,
        tools=body.tools,
    )
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    from app.services.agent_service import _rag_doc_count

    doc_count = await asyncio.to_thread(_rag_doc_count, str(agent.id))
    return _agent_detail(agent, doc_count)


@router.delete(
    "/agents/{agent_id}",
    status_code=204,
    summary="Delete agent (soft)",
    operation_id="deleteAgent",
)
async def delete_agent_by_id(
    agent_id: UUID,
    user_id: str | None = Query(None, description="Require owner"),
    soft: bool = Query(True, description="Soft delete (default) or hard delete"),
) -> None:
    if not get_settings().database_configured:
        raise HTTPException(status_code=503, detail="Database not configured")
    ok = await asyncio.to_thread(delete_agent_db, agent_id, user_id=user_id, soft=soft)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")


@router.post(
    "/update_agent_prompt_geminimesh",
    response_model=UpdateAgentGeminimeshResponse,
    summary="Update agent prompt in GeminiMesh",
    description="Generate an optimized prompt from agent config and POST it to GeminiMesh /agents. "
    "Requires GEMINIMESH_API_TOKEN. Also initializes/updates local RAG storage for the agent.",
    operation_id="updateAgentPromptGeminimesh",
)
async def update_agent_prompt_geminimesh(
    config: AgentConfig,
) -> UpdateAgentGeminimeshResponse:
    if not get_settings().geminimesh_configured:
        raise HTTPException(
            status_code=400,
            detail="GEMINIMESH_API_TOKEN not configured in environment",
        )
    if not config.agent_id:
        raise HTTPException(status_code=400, detail="agent_id is required")

    def _do_update() -> UpdateAgentGeminimeshResponse:
        optimized_prompt, _ = optimize_agent_prompt(config)
        geminimesh_data = update_agent_in_geminimesh(
            agent_id=config.agent_id,
            name=config.name,
            prompt=optimized_prompt,
        )
        rag = get_or_create_retriever(config.agent_id)
        return UpdateAgentGeminimeshResponse(
            status="success",
            agent_id=config.agent_id,
            geminimesh_response=geminimesh_data,
            optimized_prompt=optimized_prompt,
            local_rag_docs=rag.count_documents(),
            message=f"Agent '{config.name}' (ID: {config.agent_id}) updated successfully",
        )

    try:
        logger.info(
            "update_agent_prompt_geminimesh start agent_id=%s name=%s",
            config.agent_id,
            config.name,
        )
        result = await asyncio.to_thread(_do_update)
        logger.info(
            "update_agent_prompt_geminimesh success agent_id=%s name=%s",
            config.agent_id,
            config.name,
        )
        return result
    except ValueError as e:
        logger.warning("update_agent_prompt_geminimesh validation error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else 502
        body = (e.response.text[:500] if e.response is not None else str(e)) or str(e)
        logger.error(
            "update_agent_prompt_geminimesh GeminiMesh API error agent_id=%s status=%s body=%s",
            config.agent_id,
            status,
            body,
            exc_info=True,
        )
        raise HTTPException(status_code=status, detail=str(e))
    except requests.RequestException as e:
        logger.error(
            "update_agent_prompt_geminimesh network error agent_id=%s: %s",
            config.agent_id,
            e,
            exc_info=True,
        )
        raise HTTPException(status_code=502, detail=f"Network error: {e}")
    except Exception as e:
        msg = str(e)
        if "API key not valid" in msg or "API_KEY_INVALID" in msg:
            logger.warning(
                "update_agent_prompt_geminimesh invalid Gemini API key agent_id=%s",
                config.agent_id,
            )
            raise HTTPException(
                status_code=401,
                detail="GEMINI_API_KEY is invalid or missing. Set a valid key in the Python API env (e.g. python/.env). Get one at https://aistudio.google.com/apikey",
            )
        logger.error(
            "update_agent_prompt_geminimesh unhandled error agent_id=%s: %s",
            config.agent_id,
            msg,
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=msg)


@router.post(
    "/optimize_prompt",
    response_model=OptimizePromptResponse,
    summary="Optimize prompt only",
    description="Generate an optimized system prompt from agent config. Does not call GeminiMesh.",
    operation_id="optimizePrompt",
)
async def optimize_prompt(config: AgentConfig) -> OptimizePromptResponse:
    try:
        optimized_prompt, analysis = await asyncio.to_thread(optimize_agent_prompt, config)
        return OptimizePromptResponse(
            optimized_prompt=optimized_prompt,
            analysis=analysis,
            model_used="gemini-3-pro-preview",
        )
    except Exception as e:
        msg = str(e)
        if "API key not valid" in msg or "API_KEY_INVALID" in msg:
            raise HTTPException(
                status_code=401,
                detail="GEMINI_API_KEY is invalid or missing. Set it in python/.env. Get a key at https://aistudio.google.com/apikey",
            )
        raise HTTPException(status_code=400, detail=msg)
