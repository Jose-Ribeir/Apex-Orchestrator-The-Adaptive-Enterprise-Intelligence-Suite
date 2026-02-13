"""Gemini 2-call pipeline: router (gemini-3-flash-preview) + dynamic generator."""

import base64
import json
import logging
import queue
import re
import threading
import time
from collections.abc import Generator, Iterator
from pathlib import Path
from typing import Any

# If no chunk arrives for this many seconds, treat stream as done (avoids hang when API doesn't close).
GENERATOR_STREAM_CHUNK_TIMEOUT_SECONDS = 15
# After a 429, do not call the generator API again for at least this many seconds (min when parsing from response).
RATE_LIMIT_BACKOFF_SECONDS = 60

# Unix time after which we may call the API again (set from 429 response retryDelay).
_rate_limit_until: float | None = None
_rate_limit_lock = threading.Lock()


def _is_quota_error(exc: BaseException) -> bool:
    if getattr(exc, "status_code", None) == 429 or getattr(exc, "code", None) == 429:
        return True
    return "429" in str(getattr(exc, "message", "")) or "RESOURCE_EXHAUSTED" in str(exc)


def _is_invalid_key_error(exc: BaseException) -> bool:
    """True if API key is invalid (400), so we should try the next key."""
    if getattr(exc, "status_code", None) == 400 or getattr(exc, "code", None) == 400:
        msg = str(getattr(exc, "message", "") or "").lower()
        err_str = str(exc).lower()
        return "api key" in msg or "api_key_invalid" in err_str or "api_key not valid" in err_str
    return False


def _should_try_next_key(exc: BaseException) -> bool:
    """True if we should retry with next API key (429 quota or 400 invalid key)."""
    return _is_quota_error(exc) or _is_invalid_key_error(exc)


def _parse_retry_seconds_from_429(exc: BaseException) -> float:
    """Parse retry delay from Gemini 429 response (RetryInfo.details or message). Returns seconds; min 1."""
    details = getattr(exc, "details", None)
    if isinstance(details, dict):
        err = details.get("error") or details
        if isinstance(err, dict):
            for d in err.get("details") or []:
                if isinstance(d, dict) and "RetryInfo" in str(d.get("@type", "")):
                    raw = d.get("retryDelay") or ""
                    if isinstance(raw, str) and raw.strip().endswith("s"):
                        try:
                            return max(1.0, float(raw.strip()[:-1].strip()))
                        except ValueError:
                            pass
    msg = str(getattr(exc, "message", "") or "")
    match = re.search(r"retry in ([\d.]+)\s*s", msg, re.IGNORECASE)
    if match:
        try:
            return max(1.0, float(match.group(1)))
        except ValueError:
            pass
    return float(RATE_LIMIT_BACKOFF_SECONDS)


def _set_rate_limit_from_429(exc: BaseException) -> None:
    """Set rate limit until time from 429 exception (parsed retryDelay, min RATE_LIMIT_BACKOFF_SECONDS)."""
    global _rate_limit_until
    parsed = _parse_retry_seconds_from_429(exc)
    backoff = max(parsed, float(RATE_LIMIT_BACKOFF_SECONDS))
    with _rate_limit_lock:
        _rate_limit_until = time.time() + backoff
    logger.info("429 backoff set to %.0fs (parsed %.1fs from response)", backoff, parsed)


def is_gemini_rate_limited() -> bool:
    """True if we are in the 429 backoff window (do not call Gemini API)."""
    global _rate_limit_until
    with _rate_limit_lock:
        if _rate_limit_until is None:
            return False
        if time.time() >= _rate_limit_until:
            _rate_limit_until = None
            return False
        return True


from google import genai

logger = logging.getLogger(__name__)
_GENERATOR_LOG_PATH = Path(__file__).resolve().parent.parent.parent / "chat_stream.log"


def _console_log(msg: str) -> None:
    import sys

    print(f"[generator] {msg}", file=sys.stderr, flush=True)


def _append_generator_log(line: str) -> None:
    try:
        with open(_GENERATOR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line.rstrip() + "\n")
    except Exception:
        pass


from google.genai import types
from pydantic import BaseModel, Field

from app.config import get_settings
from app.prompt_registry import (
    HUMAN_ESCALATION_TOOL,
    build_optimized_prompt_with_registry,
)
from app.prompt_registry import (
    build_system_prompt_from_agent as _build_system_prompt_from_agent_shared,
)
from app.schemas.requests import AgentConfig


class RouterDecision(BaseModel):
    """Structured output from router; reasoning first for Chain-of-Thought before committing to flags."""

    reasoning: str = Field(
        ...,
        description="Brief step-by-step analysis of why tools are or are not needed",
    )
    needs_rag: bool = Field(..., description="Whether to use RAG retrieval")
    tools_needed: list[str] = Field(
        default_factory=list,
        description="e.g. ['RAG'], ['RAG','Calculator'], []",
    )
    connections_needed: list[str] = Field(
        default_factory=list,
        description="e.g. ['google_gmail'] or []",
    )
    model_to_use: str = Field(
        ...,
        description="Gemini 3 only: gemini-3-flash-preview or gemini-3-pro-preview",
    )
    complexity_score: int | None = Field(None, description="1-5, helps with model selection")


CHEAP_ROUTER_TEMPLATE = """
You are the APEX Router. Your job is to analyze a user QUERY and determine ALL tools and connections that may be needed to answer it.

AGENT: {agent_name}
AVAILABLE TOOLS:
{tools_list}
(Note: Include every tool that may be used—e.g. if the query needs both document lookup and data/parts lookup, include both RAG and Python Interpreter. Only omit tools for simple greetings or general knowledge.)

AVAILABLE CONNECTIONS:
{connections_list}

QUERY: "{query}"

INSTRUCTIONS:
1. Analyze the intent of the query.
2. Determine if external data (RAG, Web, Connections) is actually needed or if the query is conversational/logic-based.
3. Output a valid JSON object.

JSON FORMAT (reasoning must be first - think before committing to flags):
{{
  "reasoning": "Brief step-by-step analysis of why tools are or are not needed.",
  "needs_rag": true/false,
  "tools_needed": ["ToolName"] or [],
  "connections_needed": ["connection_key"] or [],
  "model_to_use": "gemini-3-flash-preview" (default) or "gemini-3-pro-preview" (complex reasoning/coding),
  "complexity_score": 1-5 (optional, helps with model selection)
}}
"""

def _get_gemini_api_keys() -> list[str]:
    """Return list of Gemini API keys (GEMINI_API_KEYS or GEMINI_API_KEY)."""
    return get_settings().get_gemini_api_keys()


def _client_for_key(key: str) -> genai.Client:
    """Create a Gemini client for the given API key."""
    return genai.Client(api_key=key)


_default_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Return Gemini client for first configured key (backward compat)."""
    global _default_client
    if _default_client is None:
        keys = _get_gemini_api_keys()
        if not keys:
            raise ValueError("No Gemini API keys configured")
        key = keys[0]
        if key:
            logger.info("Gemini client using key ending in ...%s (%d keys configured)", key[-4:] if len(key) >= 4 else "****", len(keys))
        _default_client = _client_for_key(key)
    return _default_client



def list_models(page_size: int = 100) -> list[dict[str, Any]]:
    """List available Gemini models (base models). Returns name and supported methods."""
    client = _get_client()
    result = client.models.list(config={"page_size": page_size, "query_base": True})
    page = getattr(result, "page", None) or []
    return [
        {
            "name": getattr(m, "name", None) or "",
            "display_name": getattr(m, "display_name", None) or "",
            "supported_generate_methods": list(getattr(m, "supported_generate_methods", None) or []),
        }
        for m in page
    ]


def run_cheap_router(
    agent_name: str,
    tools_list: str,
    query: str,
    connections_list: list[str] | list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call router (gemini-3-flash-preview) to get needs_rag, tools_needed, connections_needed, model_to_use.
    connections_list can be list of provider keys (str) or list of dicts with 'key' and optional 'description'.
    """
    global _rate_limit_until
    if connections_list and isinstance(connections_list[0], dict):
        connection_keys = [c.get("key") or "" for c in connections_list if c.get("key")]
        connections_display = "; ".join(
            f"{c.get('key', '')}: {c.get('description', '')}".strip().rstrip(":") or c.get("key", "")
            for c in connections_list
        )
    else:
        connection_keys = list(connections_list or [])
        connections_display = json.dumps(connection_keys)
    fallback = {
        "needs_rag": True,
        "tools_needed": ["RAG"],
        "connections_needed": [],
        "model_to_use": "gemini-3-flash-preview",
        "reasoning": "fallback",
    }
    # If we hit 429 recently, don't call the API until backoff has passed
    if is_gemini_rate_limited():
        logger.warning(
            "router skipping API call (429 backoff); returning fallback",
        )
        return fallback
    keys = _get_gemini_api_keys()
    prompt = CHEAP_ROUTER_TEMPLATE.format(
        agent_name=agent_name,
        tools_list=tools_list,
        connections_list=connections_display,
        query=query,
    )
    last_exc: BaseException | None = None
    for key_idx, key in enumerate(keys):
        client = _client_for_key(key)
        try:
            resp = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RouterDecision.model_json_schema(),
                ),
            )
            text = (getattr(resp, "text", None) or "").strip()
            if not text:
                logger.warning("router empty response text query_len=%s", len(query))
                return fallback
            data = json.loads(text)
            raw_model = str(data.get("model_to_use") or "gemini-3-flash-preview")
            # Enforce Gemini 3 only; normalize to flash or pro
            if "gemini-3-pro" in raw_model:
                raw_model = "gemini-3-pro-preview"
            elif "gemini-3" not in raw_model:
                raw_model = "gemini-3-flash-preview"
            # Normalize connections_needed to match our keys (e.g. google_gmail)
            raw_conn = list(data.get("connections_needed") or [])
            connections_needed = [c for c in raw_conn if c in connection_keys]
            # Strip Human Escalation from tools_needed: human-needed is decided by the generator's
            # final output (e.g. "Human Supervisor Review Required" marker), not by the router
            raw_tools = list(data.get("tools_needed") or [])
            tools_needed = [t for t in raw_tools if (t or "").strip() != HUMAN_ESCALATION_TOOL]
            return {
                "needs_rag": bool(data.get("needs_rag", True)),
                "tools_needed": tools_needed,
                "connections_needed": connections_needed,
                "model_to_use": raw_model,
                "reasoning": str(data.get("reasoning") or data.get("reason") or "ok"),
            }
        except Exception as e:
            last_exc = e
            if _should_try_next_key(e):
                logger.info("router error on key %s/%s (429/invalid), trying next key", key_idx + 1, len(keys))
                if key_idx < len(keys) - 1:
                    continue
                if _is_quota_error(e):
                    _set_rate_limit_from_429(e)
            logger.warning("router fallback query_len=%s error=%s", len(query), e, exc_info=True)
            return fallback
    return fallback


def _resolve_generator_model(model_name: str) -> str:
    """Return Gemini 3 model only; any non-v3 choice becomes gemini-3-flash-preview."""
    name = (model_name or "").strip() or "gemini-3-flash-preview"
    if "gemini-3-pro" in name:
        return "gemini-3-pro-preview"
    if "gemini-3" in name:
        return name
    return "gemini-3-flash-preview"


def _build_contents(full_prompt: str, attachments: list[dict[str, str]] | None) -> Any:
    """Build contents for generate_content_stream: string or multimodal parts."""
    if not attachments:
        return full_prompt
    try:
        Content = getattr(types, "Content", None)
        Part = getattr(types, "Part", None)
        Blob = getattr(types, "Blob", None)
        if not all((Content, Part, Blob)):
            return full_prompt
        parts: list[Any] = [Part(text=full_prompt)]
        for att in attachments:
            mime = att.get("mime_type") or "application/octet-stream"
            b64 = att.get("data_base64") or ""
            try:
                data = base64.b64decode(b64, validate=True)
            except Exception:
                continue
            parts.append(Part(inline_data=Blob(mime_type=mime, data=data)))
        return [Content(role="user", parts=parts)]
    except Exception as e:
        logger.warning("_build_contents failed (multimodal), falling back to text only: %s", e, exc_info=True)
        return full_prompt


def _stream_with_chunk_timeout(
    stream: Iterator[Any],
    timeout_seconds: float = GENERATOR_STREAM_CHUNK_TIMEOUT_SECONDS,
    retry_429_ref: list[bool] | None = None,
) -> Generator[Any, None, None]:
    """Consume stream in a thread; yield chunks with a per-chunk timeout so we never hang indefinitely.
    If retry_429_ref is provided, set retry_429_ref[0]=True when a 429 is caught (caller can retry with next key)."""
    q: queue.Queue[Any] = queue.Queue()
    sentinel = object()
    put_count: list[int] = [0]

    def consume() -> None:
        try:
            for chunk in stream:
                q.put(chunk)
                put_count[0] += 1
        except Exception as e:
            if _should_try_next_key(e):
                if retry_429_ref is not None:
                    retry_429_ref[0] = True
                if _is_quota_error(e):
                    _set_rate_limit_from_429(e)
            logger.warning(
                "generator_stream consume thread error chunks_put=%s: %s",
                put_count[0],
                e,
                exc_info=True,
            )
        finally:
            q.put(sentinel)

    t = threading.Thread(target=consume, daemon=True)
    t.start()
    yielded = 0
    while True:
        try:
            chunk = q.get(timeout=timeout_seconds)
        except queue.Empty:
            logger.warning(
                "generator_stream chunk timeout after %ss (no chunk for %s s); ending stream. chunks_received=%s",
                timeout_seconds,
                timeout_seconds,
                yielded,
            )
            break
        if chunk is sentinel:
            logger.info(
                "generator_stream normal end; chunks_received=%s",
                yielded,
            )
            break
        yielded += 1
        yield chunk


def run_generator_stream(
    full_prompt: str,
    generator_model_name: str,
    tool_decision: dict[str, Any],
    input_chars: int,
    docs_count: int,
    total_docs: int,
    attachments: list[dict[str, str]] | None = None,
) -> Generator[str, None, None]:
    """Stream generator model response; yields NDJSON lines. Supports optional multimodal attachments.
    Uses a per-chunk timeout so if the API stream never closes (e.g. after safety/human-review style
    responses), we still finish and yield is_final instead of hanging.
    Tries multiple GEMINI_API_KEYS on 429."""
    global _rate_limit_until
    keys = _get_gemini_api_keys()
    model_name = _resolve_generator_model(generator_model_name)
    output_chars = 0
    output_tokens = 0
    contents = _build_contents(full_prompt, attachments)
    attachment_count = len(attachments) if attachments else 0
    logger.info(
        "generator_stream start model=%s prompt_chars=%s attachment_count=%s",
        model_name,
        len(full_prompt),
        attachment_count,
    )
    _console_log(f"start model={model_name} prompt_chars={len(full_prompt)} attachment_count={attachment_count}")
    _append_generator_log(
        f"generator_stream start model={model_name} prompt_chars={len(full_prompt)} attachment_count={attachment_count}"
    )

    # If we hit 429 recently, don't call the API again until backoff has passed
    if is_gemini_rate_limited():
        with _rate_limit_lock:
            remaining = (_rate_limit_until or 0) - time.time()
        logger.warning(
            "generator_stream skipping API call (429 backoff, %.0fs remaining)",
            max(0, remaining),
        )
        yield (
            json.dumps(
                {
                    "text": "Gemini API quota exceeded (429). Please try again in a minute or check your plan: https://ai.google.dev/gemini-api/docs/rate-limits",
                    "metrics": {
                        "call_count": 2,
                        "input_chars": input_chars,
                        "output_chars": 0,
                        "generator_model": model_name,
                    },
                }
            )
            + "\n"
        )
        yield (
            json.dumps(
                {
                    "text": "",
                    "is_final": True,
                    "metrics": {
                        "total_calls": 2,
                        "router_model": "gemini-3-flash-preview",
                        "generator_model": model_name,
                        "tools_used": tool_decision.get("tools_needed", []),
                        "connections_used": tool_decision.get("connections_needed", []),
                        "docs_retrieved": docs_count,
                        "total_docs": total_docs,
                        "total_tokens": 0,
                    },
                }
            )
            + "\n"
        )
        return

    def _yield_429_error() -> Generator[str, None, None]:
        yield (
            json.dumps(
                {
                    "text": "Gemini API quota exceeded (429). Please try again later or check your plan: https://ai.google.dev/gemini-api/docs/rate-limits",
                    "metrics": {
                        "call_count": 2,
                        "input_chars": input_chars,
                        "output_chars": 0,
                        "generator_model": model_name,
                    },
                }
            )
            + "\n"
        )
        yield (
            json.dumps(
                {
                    "text": "",
                    "is_final": True,
                    "metrics": {
                        "total_calls": 2,
                        "router_model": "gemini-3-flash-preview",
                        "generator_model": model_name,
                        "tools_used": tool_decision.get("tools_needed", []),
                        "connections_used": tool_decision.get("connections_needed", []),
                        "docs_retrieved": docs_count,
                        "total_docs": total_docs,
                        "total_tokens": 0,
                    },
                }
            )
            + "\n"
        )

    def _chunk_text(chunk: Any) -> str:
        """Safely extract text from a stream chunk; chunk.text can raise ValueError for non-text content."""
        try:
            t = getattr(chunk, "text", None)
            if t is not None and isinstance(t, str):
                return t or ""
        except (ValueError, AttributeError):
            pass
        candidates = getattr(chunk, "candidates", None) or []
        if not candidates:
            return ""
        c0 = candidates[0]
        content = getattr(c0, "content", None)
        if content is None:
            return ""
        parts = getattr(content, "parts", None) or []
        return "".join(getattr(p, "text", None) or "" for p in parts if getattr(p, "text", None))

    raw_stream = None
    for key_idx, key in enumerate(keys):
        client = _client_for_key(key)
        retry_429_ref: list[bool] = [False]
        try:
            raw_stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
            )
        except Exception as e:
            if _should_try_next_key(e):
                logger.info("generator error on key %s/%s (429/invalid), trying next key", key_idx + 1, len(keys))
                if key_idx < len(keys) - 1:
                    continue
                if _is_quota_error(e):
                    _set_rate_limit_from_429(e)
                yield from _yield_429_error()
                return
            _console_log(f"generate_content_stream error: {e!s}")
            logger.warning("generator_stream fallback to flash after error: %s", e)
            _append_generator_log(f"generator_stream generate_content_stream error: {e!s}")
            try:
                raw_stream = client.models.generate_content_stream(
                    model="gemini-3-flash-preview",
                    contents=contents,
                )
            except Exception as e2:
                if _should_try_next_key(e2):
                    logger.info("generator error on key %s/%s (fallback, 429/invalid), trying next key", key_idx + 1, len(keys))
                    if key_idx < len(keys) - 1:
                        continue
                    if _is_quota_error(e2):
                        _set_rate_limit_from_429(e2)
                yield from _yield_429_error()
                return
            _console_log(f"fallback also failed: {e2!s}")
            _append_generator_log(f"generator_stream fallback also failed: {e2!s}")
            raise

        stream = _stream_with_chunk_timeout(raw_stream, retry_429_ref=retry_429_ref)
        chunk_count = 0
        last_finish_reason: Any = None
        last_block_reason: Any = None
        prompt_feedback: Any = None
        for chunk in stream:
            chunk_count += 1
            text = _chunk_text(chunk)
            if text:
                output_chars += len(text)
                output_tokens += len(text) // 4
                yield (
                    json.dumps(
                        {
                            "text": text,
                            "metrics": {
                                "call_count": 2,
                                "input_chars": input_chars,
                                "output_chars": output_chars,
                                "input_tokens": input_chars // 4,
                                "output_tokens": output_tokens,
                                "generator_model": model_name,
                            },
                        }
                    )
                    + "\n"
                )
            candidates = getattr(chunk, "candidates", None) or []
            if candidates:
                c0 = candidates[0]
                last_finish_reason = getattr(c0, "finish_reason", None)
                if last_finish_reason is not None:
                    logger.info(
                        "generator_stream seen finish_reason=%s, ending stream",
                        last_finish_reason,
                    )
                    break
            prompt_feedback = getattr(chunk, "prompt_feedback", None)
            if prompt_feedback is not None:
                last_block_reason = getattr(prompt_feedback, "block_reason", None)

        if chunk_count == 0 and retry_429_ref[0] and key_idx < len(keys) - 1:
            logger.info("generator 429 in stream on key %s/%s, trying next key", key_idx + 1, len(keys))
            continue

        if output_chars == 0:
            if last_finish_reason is not None or last_block_reason is not None:
                logger.warning(
                    "generator_stream empty response chunks=%s finish_reason=%s block_reason=%s",
                    chunk_count,
                    last_finish_reason,
                    last_block_reason,
                )
                msg = "Response was blocked or empty."
            else:
                if retry_429_ref[0] and key_idx < len(keys) - 1:
                    continue
                with _rate_limit_lock:
                    _rate_limit_until = time.time() + RATE_LIMIT_BACKOFF_SECONDS
                logger.warning(
                    "generator_stream no chunks (e.g. API error/429) chunks=%s",
                    chunk_count,
                )
                msg = "The model did not return a response. This can happen if the API quota was exceeded (429). Please try again later."
            yield (
                json.dumps(
                    {
                        "text": msg,
                        "metrics": {
                            "call_count": 2,
                            "input_chars": input_chars,
                            "output_chars": 0,
                            "generator_model": model_name,
                        },
                    }
                )
                + "\n"
            )
            output_tokens = output_tokens or 0

        logger.info(
            "generator_stream loop done chunks=%s output_chars=%s; yielding is_final",
            chunk_count,
            output_chars,
        )
        _console_log(
            f"loop_done chunks={chunk_count} output_chars={output_chars} finish_reason={last_finish_reason} block_reason={last_block_reason}"
        )
        _append_generator_log(
            f"generator_stream loop_done chunks={chunk_count} output_chars={output_chars} finish_reason={last_finish_reason} block_reason={last_block_reason}"
        )
        yield (
            json.dumps(
                {
                    "text": "",
                    "is_final": True,
                    "metrics": {
                        "total_calls": 2,
                        "router_model": "gemini-3-flash-preview",
                        "generator_model": model_name,
                        "tools_used": tool_decision.get("tools_needed", []),
                        "connections_used": tool_decision.get("connections_needed", []),
                        "docs_retrieved": docs_count,
                        "total_docs": total_docs,
                        "total_tokens": output_tokens,
                    },
                }
            )
            + "\n"
        )
        break


def optimize_agent_prompt(config: AgentConfig) -> tuple[str, dict[str, Any]]:
    """Run analysis and build optimized prompt; returns (optimized_prompt, analysis)."""
    client = _get_client()
    analysis_prompt = f"""
    AGENT: {config.name}, MODE: {config.mode}
    INSTRUCTIONS: {json.dumps(config.instructions)}
    TOOLS: {config.tools}

    JSON ONLY:
    {{
      "agent_type": "engineering|sales|research|creative|general",
      "complexity": "low|medium|high",
      "needs_rag": {str(bool(config.tools)).lower()}
    }}
    """
    resp = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=analysis_prompt,
    )
    raw = (resp.text or "").strip()
    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        analysis = {
            "agent_type": "general",
            "complexity": "medium",
            "needs_rag": bool(config.tools),
        }
    prompt = build_optimized_prompt_with_registry(
        name=config.name,
        mode=config.mode,
        instructions=config.instructions,
        tools=config.tools,
        analysis_json=analysis,
    )
    return prompt, analysis


def build_system_prompt_from_agent(
    name: str,
    mode: str,
    instructions: list[str],
    tools: list[str],
    prompt_override: str | None = None,
) -> str:
    """Build system prompt string from agent fields (for chat when agent_id is provided)."""
    return _build_system_prompt_from_agent_shared(
        name=name,
        mode=mode,
        instructions=instructions,
        tools=tools,
        prompt_override=prompt_override,
    )


def build_optimized_prompt(config: AgentConfig, analysis: dict[str, Any]) -> str:
    """Build final optimized system prompt from config and analysis."""
    return build_optimized_prompt_with_registry(
        name=config.name,
        mode=config.mode,
        instructions=config.instructions,
        tools=config.tools,
        analysis_json=analysis,
    )
