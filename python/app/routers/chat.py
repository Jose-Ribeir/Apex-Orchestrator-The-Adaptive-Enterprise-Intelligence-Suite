"""Streaming chat with 2-call router + dynamic generator."""

import asyncio
import base64
import json
import logging
import time
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.auth.deps import get_current_user_optional
from app.config import get_settings
from app.prompt_registry import get_router_tools_line
from app.schemas.requests import ChatRequest
from app.services import connections_service, gmail_service, human_tasks_service
from app.services.agent_service import get_agent
from app.services.document_parser import csv_to_text
from app.services.llm import build_system_prompt_from_agent, run_cheap_router, run_generator_stream
from app.services.rag import get_or_create_retriever

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])

_CHAT_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "chat_stream.log"


# Ensure chat logs go to chat_stream.log so they can be read without terminal access
def _ensure_chat_file_handler() -> None:
    has_file = any(getattr(h, "baseFilename", "") == str(_CHAT_LOG_PATH) for h in logger.handlers)
    if not has_file:
        try:
            fh = logging.FileHandler(_CHAT_LOG_PATH, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
            logger.addHandler(fh)
        except Exception:
            pass


def _append_chat_log(line: str) -> None:
    """Append one line to chat_stream.log so logs can be read without terminal access."""
    _ensure_chat_file_handler()
    try:
        with open(_CHAT_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
            f.flush()
    except Exception:
        pass


# When the model outputs these phrases, strip them from the user-visible response (still create human task).
HUMAN_REVIEW_MARKER = "Human Supervisor Review Required"
# Strip critical-issue escalation text so the user sees only the natural message
HIDDEN_FROM_USER_PHRASES = [
    "⚠️ CRITICAL ISSUE DETECTED: Human Supervisor Review Required.",
    "⚠️ CRITICAL ISSUE DETECTED:",
    "CRITICAL ISSUE DETECTED: Human Supervisor Review Required.",
    "CRITICAL ISSUE DETECTED:",
    "CRITICAL ISSUE DETECTED",
    HUMAN_REVIEW_MARKER,
]


def _strip_hidden_phrases(text: str) -> str:
    """Remove escalation markers so they are not shown to the user."""
    out = text
    for phrase in HIDDEN_FROM_USER_PHRASES:
        out = out.replace(phrase, "")
    return out


# Max length to store for model_response (avoid huge DB rows)
_MODEL_RESPONSE_MAX_CHARS = 100_000
# Cap flow_log payload for human tasks (retrieved docs and prompt sent)
_FLOW_LOG_PROMPT_MAX_CHARS = 100_000
_RETRIEVED_DOCS_MAX = 50
_RETRIEVED_DOC_CONTENT_MAX = 2_000


def _insert_model_query_sync(payload: dict[str, Any]) -> None:
    """Best-effort insert one ModelQuery with optional flow_log. Logs and ignores errors."""
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
                    flow_log=payload.get("flow_log"),
                    total_tokens=payload.get("total_tokens"),
                    duration_ms=payload.get("duration_ms"),
                    quality_score=payload.get("quality_score"),
                )
            )
    except Exception as e:
        logger.warning("Background ModelQuery insert failed: %s", e)


def _insert_model_query_sync_return_id(payload: dict[str, Any]) -> str | None:
    """Insert one ModelQuery and return its id (for human-task flow). Returns None on error."""
    try:
        import uuid as uuid_mod

        from app.db import session_scope
        from app.models import ModelQuery

        agent_id = uuid_mod.UUID(payload["agent_id"])
        with session_scope() as session:
            mq = ModelQuery(
                agent_id=agent_id,
                user_query=payload["user_query"],
                model_response=payload.get("model_response"),
                method_used=payload.get("method_used", "EFFICIENCY"),
                flow_log=payload.get("flow_log"),
                total_tokens=payload.get("total_tokens"),
                duration_ms=payload.get("duration_ms"),
                quality_score=payload.get("quality_score"),
            )
            session.add(mq)
            session.flush()
            return str(mq.id)
    except Exception as e:
        logger.warning("ModelQuery insert (human task) failed: %s", e)
        return None


def _rag_key(request: ChatRequest, *, resolved_agent_name: str) -> str:
    """RAG namespace key: agent_id when provided (matches indexing), else agent_name (legacy)."""
    if request.agent_id and str(request.agent_id).strip():
        return str(request.agent_id).strip()
    return resolved_agent_name.strip()


def _resolve_agent_name_and_prompt(request: ChatRequest) -> tuple[str, str, Any] | None:
    """
    When request.agent_id is set, load agent and build system_prompt; return (agent_name, system_prompt, agent).
    When not set (legacy), return (agent_name, system_prompt, None).
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
        return (agent.name, system_prompt, agent)
    agent_name = (request.agent_name or "").strip()
    system_prompt = (request.system_prompt or "").strip()
    return (agent_name, system_prompt, None)


def _run_stream_pipeline(
    request: ChatRequest,
    model_query_payload: list[dict[str, Any]] | None = None,
    user_id: str | None = None,
):
    """Blocking: router + RAG + generator stream. Yields NDJSON lines.
    If model_query_payload and agent_id + DB are set, appends one dict for ModelQuery insert.
    When user_id is set and router returns connections_needed including 'google', Gmail is searched and added to context."""  # noqa: E501
    # Log request (full flow will be logged after response)
    attachment_count = len(request.attachments) if request.attachments else 0
    first_mime = (request.attachments[0].mime_type or "") if request.attachments else ""
    logger.info(
        "model_query_start agent_id=%s user_query_len=%s attachment_count=%s first_mime=%s",
        request.agent_id or "(legacy)",
        len(request.message or ""),
        attachment_count,
        first_mime or "(none)",
    )
    _console_log(
        f"model_query_start agent_id={request.agent_id} attachment_count={attachment_count} first_mime={first_mime or '(none)'}"
    )
    _append_chat_log(
        f"model_query_start agent_id={request.agent_id} user_query_len={len(request.message or '')} attachment_count={attachment_count} first_mime={first_mime or '(none)'}"
    )
    resolved = _resolve_agent_name_and_prompt(request)
    if resolved is None:
        yield json.dumps({"error": "Agent not found", "detail": f"Agent {request.agent_id} not found"}) + "\n"
        return
    agent_name, system_prompt, agent = resolved

    if agent is not None:
        tool_names = [at.tool.name for at in agent.agent_tools]
        tools_list = get_router_tools_line(tool_names)
    else:
        tools_line = next(
            (line for line in system_prompt.split("\n") if "TOOLS:" in line),
            "TOOLS: []",
        )
        tools_list = tools_line.split("TOOLS: ")[1].split("\n")[0] if "TOOLS:" in tools_line else "[]"
    try:
        connections_list = connections_service.list_connection_types_for_router()
    except Exception:
        connections_list = []
    tool_decision = run_cheap_router(
        agent_name=agent_name,
        tools_list=tools_list,
        query=request.message,
        connections_list=connections_list,
    )
    rag = get_or_create_retriever(_rag_key(request, resolved_agent_name=agent_name))
    context_str = ""
    docs_count = 0
    total_docs = rag.count_documents()
    rag_search_results: list[dict[str, Any]] = []

    # Long context mode: when enabled and total docs under cap, use raw docs instead of vector search
    long_context_used = False
    if agent is not None and total_docs > 0:
        if agent.resolved_metadata.get("long_context_enabled"):
            max_tokens = agent.resolved_metadata.get("long_context_max_tokens", 1_000_000)
            result = rag.get_all_content_for_context(max_tokens)
            if result is not None:
                context_str, _est_tokens = result
                docs_count = total_docs
                long_context_used = True
                logger.info(
                    "Long context: key=%s total_docs=%s estimated_tokens=%s",
                    _rag_key(request, resolved_agent_name=agent_name),
                    total_docs,
                    _est_tokens,
                )

    if not long_context_used and tool_decision.get("needs_rag", False):
        try:
            results = rag.search(request.message)
            rag_search_results = results
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
            rag_search_results = []
    # When user is authenticated and router asked for Gmail, search or list messages and add to context
    gmail_context_for_actions = ""
    if user_id and "google_gmail" in tool_decision.get("connections_needed", []):
        token = connections_service.get_valid_access_token(user_id, "google_gmail")
        if token:
            try:
                q = gmail_service.generate_gmail_query(request.message or "")
                if q:
                    gmail_text = gmail_service.search_gmail(token, q=q, max_results=15)
                    context_str += f"\n\n[GMAIL - search: {q!r}]\n{gmail_text}"
                else:
                    gmail_text = connections_service.fetch_gmail_recent_summary(token, max_messages=10)
                    context_str += "\n\n[GMAIL - recent messages]\n" + gmail_text
                gmail_context_for_actions = gmail_text
            except Exception as e:
                logger.warning("Gmail context fetch failed: %s", e)
                context_str += "\n\n[GMAIL: could not load messages.]"
        else:
            context_str += "\n\n[GMAIL: not connected. Connect Gmail in Connections to see emails here.]"
    # Parse CSV attachments and append text to context (non-CSV attachments go to run_generator_stream)
    if request.attachments:
        for a in request.attachments:
            mime = (a.mime_type or "").lower()
            if mime in ("text/csv", "application/csv"):
                try:
                    raw = base64.b64decode(a.data_base64, validate=True)
                    csv_text = csv_to_text(raw)
                    if csv_text.strip():
                        context_str += f"\n\n[CSV ATTACHMENT]\n{csv_text}"
                except Exception as e:
                    logger.warning("Failed to parse CSV attachment: %s", e)
    generator_model_name = tool_decision.get("model_to_use", "gemini-3-flash-preview")
    full_prompt = f"""
[SYSTEM]{system_prompt}

[ROUTER]{json.dumps(tool_decision)}

[CONTEXT]{context_str}

[QUERY]{request.message}
"""
    input_chars = len(full_prompt)

    if agent is not None:
        tools_available = [at.tool.name for at in agent.agent_tools]
        if "RAG" not in tools_available:
            tools_available = ["RAG"] + list(tools_available)
        agent_mode = (getattr(agent, "mode", None) or "EFFICIENCY").strip()
    else:
        try:
            tools_available = json.loads(tools_list) if isinstance(tools_list, str) else (tools_list or [])
        except (json.JSONDecodeError, TypeError):
            tools_available = []
        if not isinstance(tools_available, list):
            tools_available = []
        agent_mode = ""
    metrics = {
        "call_count": 1,
        "router_model": "gemini-3-flash-preview",
        "generator_model": generator_model_name,
        "agent_mode": agent_mode,
        "tools_available": tools_available,
        "tools_executed": tool_decision.get("tools_needed", []),
        "connections_used": tool_decision.get("connections_needed", []),
        "docs_retrieved": docs_count,
        "total_docs": total_docs,
        "input_chars": input_chars,
    }
    first_line = (
        json.dumps(
            {
                "router_decision": tool_decision,
                "metrics": metrics,
            }
        )
        + "\n"
    )
    yield first_line
    accumulated_text: list[str] = []
    stream_total_tokens: int | None = None
    start_time = time.perf_counter()
    attachments_list: list[dict[str, str]] | None = None
    if request.attachments:
        csv_mimes = {"text/csv", "application/csv"}
        attachments_list = [
            {"mime_type": a.mime_type, "data_base64": a.data_base64}
            for a in request.attachments
            if (a.mime_type or "").lower() not in csv_mimes
        ]
        if not attachments_list:
            attachments_list = None
    logger.info(
        "chat_stream generator_loop_start agent_id=%s model=%s has_attachments=%s",
        request.agent_id,
        generator_model_name,
        attachments_list is not None and len(attachments_list) > 0,
    )
    line_count = 0
    human_review_content_triggered = False
    for line in run_generator_stream(
        full_prompt,
        generator_model_name,
        tool_decision,
        input_chars,
        docs_count,
        total_docs,
        attachments=attachments_list,
    ):
        line_count += 1
        try:
            parsed = json.loads(line)
            if isinstance(parsed.get("text"), str):
                # Strip escalation phrases from display; do not truncate the rest
                chunk_text = _strip_hidden_phrases(parsed["text"])
                if HUMAN_REVIEW_MARKER in parsed["text"]:
                    human_review_content_triggered = True
                accumulated_text.append(parsed["text"])  # keep original for response_text / human task
                line = json.dumps({**parsed, "text": chunk_text}) + "\n"
            if parsed.get("is_final"):
                metrics = parsed.get("metrics") or {}
                stream_total_tokens = metrics.get("total_tokens")
                logger.info(
                    "chat_stream is_final received line_count=%s response_chars=%s",
                    line_count,
                    sum(len(t) for t in accumulated_text),
                )
        except (json.JSONDecodeError, TypeError):
            pass
        yield line
    response_text = "".join(accumulated_text)
    duration_ms = int((time.perf_counter() - start_time) * 1000)
    has_attachments = attachments_list is not None and len(attachments_list) > 0
    logger.info(
        "chat_stream generator_loop_finished agent_id=%s line_count=%s response_chars=%s duration_ms=%s has_attachments=%s",
        request.agent_id,
        line_count,
        len(response_text),
        duration_ms,
        has_attachments,
    )
    _console_log(
        f"generator_loop_finished agent_id={request.agent_id} response_chars={len(response_text)} duration_ms={duration_ms} has_attachments={has_attachments}"
    )
    _append_chat_log(
        f"generator_loop_finished agent_id={request.agent_id} line_count={line_count} response_chars={len(response_text)} duration_ms={duration_ms} has_attachments={has_attachments}"
    )
    # Log model response output for debugging (truncated)
    if response_text:
        preview = response_text[:500] + "..." if len(response_text) > 500 else response_text
        short_preview = (preview[:80] + "...") if len(preview) > 80 else preview
        _console_log(
            f"model_response_preview agent_id={request.agent_id} response_chars={len(response_text)} preview={short_preview!r}"
        )
        logger.info("chat_stream model_response_preview agent_id=%s preview=%s", request.agent_id, preview)
        _append_chat_log(
            f"model_response_preview agent_id={request.agent_id} response_chars={len(response_text)} preview={preview!r}"
        )
    else:
        _console_log(f"model_response_empty agent_id={request.agent_id} line_count={line_count} response_chars=0")
        logger.warning("chat_stream model_response_empty agent_id=%s line_count=%s", request.agent_id, line_count)
        _append_chat_log(f"model_response_empty agent_id={request.agent_id} line_count={line_count} response_chars=0")
    human_task_created = False

    # Model output requested human review (e.g. "Human Supervisor Review Required" in response)
    if (
        human_review_content_triggered
        and not human_task_created
        and get_settings().database_configured
        and model_query_payload is not None
        and request.agent_id
        and str(request.agent_id).strip()
    ):
        logger.info(
            "chat_stream creating human_task (content-triggered) agent_id=%s",
            request.agent_id,
        )
        response_truncated = (
            response_text[:_MODEL_RESPONSE_MAX_CHARS] + "\n...[truncated]"
            if len(response_text) > _MODEL_RESPONSE_MAX_CHARS
            else response_text
        )
        flow_log_metrics_ct: dict[str, Any] = {
            "call_count": 1,
            "router_model": "gemini-3-flash-preview",
            "generator_model": tool_decision.get("model_to_use", "gemini-3-flash-preview"),
            "tools_executed": tool_decision.get("tools_needed", []),
            "docs_retrieved": docs_count,
            "total_docs": total_docs,
            "input_chars": input_chars,
            "response_chars": len(response_text),
            "duration_ms": duration_ms,
        }
        if stream_total_tokens is not None:
            flow_log_metrics_ct["total_tokens"] = stream_total_tokens
        if long_context_used:
            retrieved_documents_ct = [{"long_context": True, "total_docs": total_docs}]
        else:
            retrieved_documents_ct = [
                {
                    "contents": (r.get("contents") or "")[:_RETRIEVED_DOC_CONTENT_MAX]
                    + ("..." if len((r.get("contents") or "")) > _RETRIEVED_DOC_CONTENT_MAX else ""),
                    "score": r.get("score"),
                }
                for r in (rag_search_results or [])[:_RETRIEVED_DOCS_MAX]
            ]
        flow_log_ct = {
            "request": {
                "agent_id": str(request.agent_id).strip(),
                "user_query": request.message,
                "user_query_len": len(request.message or ""),
            },
            "router_decision": tool_decision,
            "metrics": flow_log_metrics_ct,
            "response_preview": (response_text[:500] + "...") if len(response_text) > 500 else response_text,
            "retrieved_documents": retrieved_documents_ct,
        }
        if long_context_used and full_prompt:
            flow_log_ct["prompt_sent_to_model"] = (
                full_prompt[:_FLOW_LOG_PROMPT_MAX_CHARS] + "\n...[truncated]"
                if len(full_prompt) > _FLOW_LOG_PROMPT_MAX_CHARS
                else full_prompt
            )
        payload_ct = {
            "agent_id": str(request.agent_id).strip(),
            "user_query": request.message,
            "model_response": response_truncated or None,
            "method_used": (tool_decision.get("model_to_use") or "EFFICIENCY").strip().upper() or "EFFICIENCY",
            "flow_log": flow_log_ct,
            "total_tokens": stream_total_tokens,
            "duration_ms": duration_ms,
        }
        model_query_id_ct = _insert_model_query_sync_return_id(payload_ct)
        if model_query_id_ct:
            try:
                task_ct = human_tasks_service.create_task(
                    model_query_id=UUID(model_query_id_ct),
                    reason="Critical issue: human supervisor review required",
                    model_message=response_text[:5000] or "",
                    retrieved_data=json.dumps(
                        {
                            "source": "content",
                            "human_review_marker": HUMAN_REVIEW_MARKER,
                            "doc_count": docs_count,
                            "long_context_used": long_context_used,
                        }
                    ),
                    status="PENDING",
                )
                human_task_created = True
                yield (
                    json.dumps(
                        {
                            "human_task": {
                                "id": str(task_ct.id),
                                "model_query_id": model_query_id_ct,
                                "reason": task_ct.reason,
                                "status": task_ct.status,
                                "model_message": (task_ct.model_message or "")[:500],
                                "retrieved_data": task_ct.retrieved_data,
                            },
                        }
                    )
                    + "\n"
                )
                logger.info(
                    "chat_stream human_task yielded (content-triggered) task_id=%s model_query_id=%s",
                    task_ct.id,
                    model_query_id_ct,
                )
            except Exception as e:
                logger.warning("Human task create (content-triggered) failed: %s", e, exc_info=True)

    # If we had Gmail context, check for email action: require human approval (insert task) or execute
    if user_id and gmail_context_for_actions and not human_task_created:
        try:
            action_data = gmail_service.extract_email_action_only(
                request.message or "",
                response_text,
                gmail_context_for_actions,
            )
            if (
                action_data
                and get_settings().database_configured
                and model_query_payload is not None
                and request.agent_id
            ):
                # Human task required: insert ModelQuery, create HumanTask, yield human_task (do not execute)
                response_truncated = (
                    response_text[:_MODEL_RESPONSE_MAX_CHARS] + "\n...[truncated]"
                    if len(response_text) > _MODEL_RESPONSE_MAX_CHARS
                    else response_text
                )
                flow_log_metrics: dict[str, Any] = {
                    "call_count": 1,
                    "router_model": "gemini-3-flash-preview",
                    "generator_model": tool_decision.get("model_to_use", "gemini-3-flash-preview"),
                    "tools_executed": tool_decision.get("tools_needed", []),
                    "docs_retrieved": docs_count,
                    "total_docs": total_docs,
                    "input_chars": input_chars,
                    "response_chars": len(response_text),
                    "duration_ms": duration_ms,
                }
                if stream_total_tokens is not None:
                    flow_log_metrics["total_tokens"] = stream_total_tokens
                flow_log = {
                    "request": {
                        "agent_id": str(request.agent_id).strip(),
                        "user_query": request.message,
                        "user_query_len": len(request.message or ""),
                    },
                    "router_decision": tool_decision,
                    "metrics": flow_log_metrics,
                    "response_preview": (response_text[:500] + "...") if len(response_text) > 500 else response_text,
                }
                payload = {
                    "agent_id": str(request.agent_id).strip(),
                    "user_query": request.message,
                    "model_response": response_truncated or None,
                    "method_used": (tool_decision.get("model_to_use") or "EFFICIENCY").strip().upper() or "EFFICIENCY",
                    "flow_log": flow_log,
                    "total_tokens": stream_total_tokens,
                    "duration_ms": duration_ms,
                }
                model_query_id = _insert_model_query_sync_return_id(payload)
                if model_query_id:
                    try:
                        task = human_tasks_service.create_task(
                            model_query_id=UUID(model_query_id),
                            reason="Email action requires approval",
                            model_message=response_text[:5000] or "",
                            retrieved_data=json.dumps(action_data),
                            status="PENDING",
                        )
                        human_task_created = True
                        yield (
                            json.dumps(
                                {
                                    "human_task": {
                                        "id": str(task.id),
                                        "model_query_id": model_query_id,
                                        "reason": task.reason,
                                        "status": task.status,
                                        "model_message": (task.model_message or "")[:500],
                                        "retrieved_data": task.retrieved_data,
                                    },
                                }
                            )
                            + "\n"
                        )
                        logger.info("Human task created for email action task_id=%s", task.id)
                    except Exception as e:
                        logger.warning("Human task create failed: %s", e, exc_info=True)
            elif not action_data:
                # No email action: run execute path (legacy) and yield email_action if any
                action_result = gmail_service.extract_and_execute_email_actions(
                    user_id,
                    request.message or "",
                    response_text,
                    gmail_context_for_actions,
                    get_token=lambda uid: connections_service.get_valid_access_token(uid, "google_gmail"),
                )
                if action_result:
                    yield json.dumps({"email_action": action_result}) + "\n"
        except Exception as e:
            logger.warning("Email action step failed: %s", e)

    if (
        model_query_payload is not None
        and request.agent_id
        and str(request.agent_id).strip()
        and get_settings().database_configured
        and not human_task_created
    ):
        if len(response_text) > _MODEL_RESPONSE_MAX_CHARS:
            response_text = response_text[:_MODEL_RESPONSE_MAX_CHARS] + "\n...[truncated]"
        flow_log_metrics = {
            "call_count": 1,
            "router_model": "gemini-3-flash-preview",
            "generator_model": tool_decision.get("model_to_use", "gemini-3-flash-preview"),
            "tools_executed": tool_decision.get("tools_needed", []),
            "docs_retrieved": docs_count,
            "total_docs": total_docs,
            "input_chars": input_chars,
            "response_chars": len(response_text),
            "duration_ms": duration_ms,
        }
        if stream_total_tokens is not None:
            flow_log_metrics["total_tokens"] = stream_total_tokens
        flow_log = {
            "request": {
                "agent_id": str(request.agent_id).strip(),
                "user_query": request.message,
                "user_query_len": len(request.message or ""),
            },
            "router_decision": tool_decision,
            "metrics": flow_log_metrics,
            "response_preview": (response_text[:500] + "...") if len(response_text) > 500 else response_text,
        }
        logger.info(
            "model_query_complete agent_id=%s method=%s docs=%s response_chars=%s",
            request.agent_id,
            tool_decision.get("model_to_use", "EFFICIENCY"),
            docs_count,
            len(response_text),
            extra={"flow_log": flow_log},
        )
        model_query_payload.append(
            {
                "agent_id": str(request.agent_id).strip(),
                "user_query": request.message,
                "model_response": response_text or None,
                "method_used": (tool_decision.get("model_to_use") or "EFFICIENCY").strip().upper() or "EFFICIENCY",
                "flow_log": flow_log,
                "total_tokens": stream_total_tokens,
                "duration_ms": duration_ms,
            }
        )


def run_chat_pipeline_collect(request: ChatRequest, user_id: str | None = None) -> str:
    """Run the stream pipeline and return the full response text (for email reply etc). Strips escalation phrases."""
    text_parts: list[str] = []
    for line in _run_stream_pipeline(request, model_query_payload=None, user_id=user_id):
        try:
            if isinstance(line, str):
                parsed = json.loads(line)
                if isinstance(parsed.get("text"), str):
                    text_parts.append(parsed["text"])
        except (json.JSONDecodeError, TypeError):
            pass
    response = _strip_hidden_phrases("".join(text_parts))
    return response.strip()


def _console_log(msg: str) -> None:
    """Write to stderr so it appears in the server terminal regardless of logging config."""
    import sys

    print(f"[chat] {msg}", file=sys.stderr, flush=True)


@router.post(
    "/generate_stream",
    summary="Stream chat (router + generator)",
    description=(
        "Call #1: router decides needs_rag, tools_needed, connections_needed, model_to_use. "
        "Call #2: dynamic generator streams. Returns NDJSON: router_decision, text chunks, final metrics."
    ),
    operation_id="generateStream",
)
async def generate_stream(
    request: ChatRequest,
    current_user: dict | None = Depends(get_current_user_optional),
):
    _console_log(f"generate_stream request agent_id={request.agent_id} message_len={len(request.message or '')}")
    logger.info(
        "generate_stream request received agent_id=%s message_len=%s", request.agent_id, len(request.message or "")
    )
    _append_chat_log(f"generate_stream request agent_id={request.agent_id} message_len={len(request.message or '')}")
    user_id = current_user["id"] if current_user else None
    queue: asyncio.Queue[str | tuple[str, dict] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    payload_holder: list[dict[str, Any]] = []

    def put(chunk: str | tuple[str, dict] | None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, chunk)

    def worker() -> None:
        _console_log(f"worker_start agent_id={request.agent_id}")
        logger.info("chat_stream worker_start agent_id=%s", request.agent_id)
        try:
            for line in _run_stream_pipeline(request, model_query_payload=payload_holder, user_id=user_id):
                put(line)
            if payload_holder:
                put(("model_query", payload_holder[0]))
        except Exception as e:
            _console_log(f"worker_error agent_id={request.agent_id} error={e!s}")
            raise
        finally:
            put(None)
            _console_log(f"worker_finished agent_id={request.agent_id}")
            logger.info("chat_stream worker_finished agent_id=%s", request.agent_id)

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
