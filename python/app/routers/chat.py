"""Streaming chat with 2-call router + dynamic generator."""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.schemas.requests import ChatRequest
from app.services.agent_service import get_agent
from app.services.llm import build_system_prompt_from_agent, run_cheap_router, run_generator_stream
from app.services.rag import get_or_create_retriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])

# Max length to store for model_response (avoid huge DB rows)
_MODEL_RESPONSE_MAX_CHARS = 100_000


def _insert_model_query_sync(payload: dict[str, Any]) -> None:
    """Best-effort insert one ModelQuery. Logs and ignores errors."""
    try:
        import uuid as uuid_mod

        from app.db import session_scope
        from app.models import ModelQuery

        agent_id = uuid_mod.UUID(payload["agent_id"])
        with session_scope() as session:
            session.add(
                ModelQuery(
                    agent_id=agent_id,
                    user_query=payload["user_query"],
                    model_response=payload.get("model_response"),
                    method_used=payload.get("method_used", "EFFICIENCY"),
                )
            )
    except Exception as e:
        logger.warning("Background ModelQuery insert failed: %s", e)


def _rag_key(request: ChatRequest, *, resolved_agent_name: str) -> str:
    """RAG namespace key: agent_id when provided (matches indexing), else agent_name (legacy)."""
    if request.agent_id and str(request.agent_id).strip():
        return str(request.agent_id).strip()
    return resolved_agent_name.strip()


def _resolve_agent_name_and_prompt(request: ChatRequest) -> tuple[str, str] | None:
    """
    When request.agent_id is set, load agent and build system_prompt; return (agent_name, system_prompt).
    When not set (legacy), return (request.agent_name, request.system_prompt).
    Returns None if agent_id was set but agent not found (caller should yield error and return).
    """
    if request.agent_id and str(request.agent_id).strip():
        agent = get_agent(request.agent_id, with_relations=True)
        if not agent:
            return None
        instructions = [i.content for i in sorted(agent.instructions, key=lambda x: x.order)]
        tools = [at.tool.name for at in agent.agent_tools]
        system_prompt = build_system_prompt_from_agent(
            name=agent.name,
            mode=agent.mode,
            instructions=instructions,
            tools=tools,
            prompt_override=agent.prompt,
        )
        return (agent.name, system_prompt)
    agent_name = (request.agent_name or "").strip()
    system_prompt = (request.system_prompt or "").strip()
    return (agent_name, system_prompt)


def _run_stream_pipeline(request: ChatRequest, model_query_payload: list[dict[str, Any]] | None = None):
    """Blocking: router + RAG + generator stream. Yields NDJSON lines.
    If model_query_payload is provided and agent_id + DB are set, appends one dict for background ModelQuery insert."""
    resolved = _resolve_agent_name_and_prompt(request)
    if resolved is None:
        yield json.dumps({"error": "Agent not found", "detail": f"Agent {request.agent_id} not found"}) + "\n"
        return
    agent_name, system_prompt = resolved

    tools_line = next(
        (line for line in system_prompt.split("\n") if "TOOLS:" in line),
        "TOOLS: []",
    )
    tools_list = tools_line.split("TOOLS: ")[1].split("\n")[0] if "TOOLS:" in tools_line else "[]"
    tool_decision = run_cheap_router(
        agent_name=agent_name,
        tools_list=tools_list,
        query=request.message,
    )
    rag = get_or_create_retriever(_rag_key(request, resolved_agent_name=agent_name))
    context_str = ""
    docs_count = 0
    total_docs = rag.count_documents()
    if tool_decision.get("needs_rag", False):
        try:
            results = rag.search(request.message)
            docs_count = len(results)
            context_str = "\n\n".join(r["contents"] for r in results)
            logger.info(
                "RAG search: key=%s docs_retrieved=%s total_docs=%s",
                _rag_key(request, resolved_agent_name=agent_name),
                docs_count,
                total_docs,
            )
            if docs_count == 0 and total_docs > 0:
                logger.warning(
                    "RAG returned 0 docs but agent has %s indexed. "
                    "Vertex index may still be updating (wait a few minutes after upload).",
                    total_docs,
                )
        except Exception as e:
            logger.warning("RAG search failed, continuing without context: %s", e, exc_info=True)
            context_str = ""
            docs_count = 0
    generator_model_name = tool_decision.get("model_to_use", "gemini-2.5-flash")
    full_prompt = f"""
[SYSTEM]{system_prompt}

[ROUTER]{json.dumps(tool_decision)}

[CONTEXT]{context_str}

[QUERY]{request.message}
"""
    input_chars = len(full_prompt)

    first_line = (
        json.dumps(
            {
                "router_decision": tool_decision,
                "metrics": {
                    "call_count": 1,
                    "router_model": "gemini-2.5-flash-lite",
                    "generator_model": generator_model_name,
                    "tools_executed": tool_decision.get("tools_needed", []),
                    "docs_retrieved": docs_count,
                },
            }
        )
        + "\n"
    )
    yield first_line
    accumulated_text: list[str] = []
    for line in run_generator_stream(
        full_prompt,
        generator_model_name,
        tool_decision,
        input_chars,
        docs_count,
        total_docs,
    ):
        try:
            parsed = json.loads(line)
            if isinstance(parsed.get("text"), str):
                accumulated_text.append(parsed["text"])
        except (json.JSONDecodeError, TypeError):
            pass
        yield line
    if (
        model_query_payload is not None
        and request.agent_id
        and str(request.agent_id).strip()
        and get_settings().database_configured
    ):
        response_text = "".join(accumulated_text)
        if len(response_text) > _MODEL_RESPONSE_MAX_CHARS:
            response_text = response_text[:_MODEL_RESPONSE_MAX_CHARS] + "\n...[truncated]"
        model_query_payload.append(
            {
                "agent_id": str(request.agent_id).strip(),
                "user_query": request.message,
                "model_response": response_text or None,
                "method_used": (tool_decision.get("model_to_use") or "EFFICIENCY").strip().upper() or "EFFICIENCY",
            }
        )


@router.post(
    "/generate_stream",
    summary="Stream chat (router + generator)",
    description=(
        "Call #1: cheap router decides needs_rag, tools_needed, model_to_use. "
        "Call #2: dynamic generator streams. Returns NDJSON: router_decision, text chunks, final metrics."
    ),
    operation_id="generateStream",
)
async def generate_stream(request: ChatRequest):
    queue: asyncio.Queue[str | tuple[str, dict] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    payload_holder: list[dict[str, Any]] = []

    def put(chunk: str | tuple[str, dict] | None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, chunk)

    def worker() -> None:
        try:
            for line in _run_stream_pipeline(request, model_query_payload=payload_holder):
                put(line)
            if payload_holder:
                put(("model_query", payload_holder[0]))
        finally:
            put(None)

    loop.run_in_executor(None, worker)

    async def ndjson_stream():
        while True:
            chunk = await queue.get()
            if chunk is None:
                break
            if isinstance(chunk, tuple) and chunk[0] == "model_query":

                async def _run_insert(p: dict[str, Any]) -> None:
                    await asyncio.to_thread(_insert_model_query_sync, p)

                task = asyncio.create_task(_run_insert(chunk[1]))

                def _done(t: asyncio.Task) -> None:
                    try:
                        t.result()
                    except Exception as e:
                        logger.warning("Background ModelQuery task failed: %s", e)

                task.add_done_callback(_done)
                continue
            yield chunk

    return StreamingResponse(
        ndjson_stream(),
        media_type="application/x-ndjson",
    )
