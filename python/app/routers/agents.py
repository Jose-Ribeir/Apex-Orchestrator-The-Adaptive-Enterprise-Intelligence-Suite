"""Agent prompt optimization and GeminiMesh update endpoints."""

import asyncio
import logging

import requests
from fastapi import APIRouter, HTTPException

from app.config import get_settings

logger = logging.getLogger("app.agents")
from app.schemas.requests import AgentConfig
from app.schemas.responses import (
    AgentInfo,
    ListAgentsResponse,
    OptimizePromptResponse,
    UpdateAgentGeminimeshResponse,
)
from app.services.gemini_router import optimize_agent_prompt
from app.services.geminimesh import update_agent_in_geminimesh
from app.services.rag import get_or_create_retriever, list_agents_with_doc_counts

router = APIRouter(tags=["Agents"])


@router.get(
    "/agents",
    response_model=ListAgentsResponse,
    summary="List agents",
    description="List all agents that have RAG data (persisted under DATA_FOLDER). "
    "Returns agent name and document count for each.",
    operation_id="listAgents",
)
async def list_agents() -> ListAgentsResponse:
    items = await asyncio.to_thread(list_agents_with_doc_counts)
    return ListAgentsResponse(agents=[AgentInfo(name=name, doc_count=count) for name, count in items])


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
        rag = get_or_create_retriever(config.name)
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
