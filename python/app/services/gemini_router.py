"""Gemini 2-call pipeline: router (gemini-3-flash-preview) + dynamic generator."""

import base64
import json
from collections.abc import Generator
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.config import get_settings
from app.schemas.requests import AgentConfig


class RouterDecision(BaseModel):
    """Structured output from router; must match Gemini response_schema."""

    needs_rag: bool = Field(..., description="Whether to use RAG retrieval")
    tools_needed: list[str] = Field(
        default_factory=list,
        description="e.g. ['RAG'], ['RAG','Calculator'], []",
    )
    connections_needed: list[str] = Field(
        default_factory=list,
        description="e.g. ['google'] or []",
    )
    model_to_use: str = Field(
        ...,
        description="e.g. gemini-2.5-flash, gemini-3-flash-preview",
    )
    reason: str = Field(..., description="One-sentence reason")
    needs_human_review: bool = Field(
        False,
        description="True when the query should be escalated or reviewed by a human (e.g. customer support, complaint, sensitive request)",
    )


ANALYSIS_V5_TEMPLATE = """
--- ROUTING LOGIC (V5) ---
Classify into Profile 1 (RETRIEVAL '1-Yes') or Profile 2 (DIRECT '2-No').
Rule: If doubt, choose '1-Yes'. Reply ONLY '1-Yes' or '2-No'.
"""

CHEAP_ROUTER_TEMPLATE = """
ROUTER (gemini-3-flash-preview) - 50 tokens max:

AGENT: {agent_name}
TOOLS: {tools_list}
CONNECTIONS: {connections_list}
QUERY: "{query}"

Output JSON only with:
- needs_rag: true/false
- tools_needed: ["RAG"]|["RAG","Calculator"]|[]
- connections_needed: ["google"]|[]
- model_to_use: "gemini-3-flash-preview"|"gemini-2.5-flash" (use flash only; pro has no free-tier quota)
- reason: "1-sentence"
- needs_human_review: true if the query should be escalated to a human (e.g. customer complaint, refund, sensitive, escalation request); otherwise false
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


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
    connections_list: list[str] | None = None,
) -> dict[str, Any]:
    """Call router (gemini-3-flash-preview) to get needs_rag, tools_needed, connections_needed, model_to_use."""
    fallback = {
        "needs_rag": True,
        "tools_needed": ["RAG"],
        "connections_needed": [],
        "model_to_use": "gemini-3-flash-preview",
        "reason": "fallback",
        "needs_human_review": False,
    }
    client = _get_client()
    connections_json = json.dumps(connections_list or [])
    prompt = CHEAP_ROUTER_TEMPLATE.format(
        agent_name=agent_name,
        tools_list=tools_list,
        connections_list=connections_json,
        query=query,
    )
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
            return fallback
        data = json.loads(text)
        raw_model = str(data.get("model_to_use") or "gemini-3-flash-preview")
        if "gemini-3-pro" in raw_model:
            raw_model = "gemini-3-flash-preview"
        return {
            "needs_rag": bool(data.get("needs_rag", True)),
            "tools_needed": list(data.get("tools_needed") or []),
            "connections_needed": list(data.get("connections_needed") or []),
            "model_to_use": raw_model,
            "reason": str(data.get("reason") or "ok"),
            "needs_human_review": bool(data.get("needs_human_review", False)),
        }
    except (json.JSONDecodeError, AttributeError, TypeError, KeyError, Exception):
        return fallback


def _resolve_generator_model(model_name: str) -> str:
    """Return model name; map pro to flash (no free-tier quota) and fallback if invalid."""
    name = (model_name or "").strip() or "gemini-3-flash-preview"
    if "gemini-3-pro" in name:
        return "gemini-3-flash-preview"
    return name


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
    except Exception:
        return full_prompt


def run_generator_stream(
    full_prompt: str,
    generator_model_name: str,
    tool_decision: dict[str, Any],
    input_chars: int,
    docs_count: int,
    total_docs: int,
    attachments: list[dict[str, str]] | None = None,
) -> Generator[str, None, None]:
    """Stream generator model response; yields NDJSON lines. Supports optional multimodal attachments."""
    client = _get_client()
    model_name = _resolve_generator_model(generator_model_name)
    output_chars = 0
    output_tokens = 0
    contents = _build_contents(full_prompt, attachments)

    try:
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=contents,
        )
    except Exception:
        model_name = "gemini-3-flash-preview"
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=contents,
        )

    for chunk in stream:
        text = getattr(chunk, "text", None) or ""
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
    prompt = build_optimized_prompt(config, analysis)
    return prompt, analysis


def build_system_prompt_from_agent(
    name: str,
    mode: str,
    instructions: list[str],
    tools: list[str],
    prompt_override: str | None = None,
) -> str:
    """Build system prompt string from agent fields (for chat when agent_id is provided)."""
    instructions_blob = "\n".join(f"- {i}" for i in instructions) if instructions else "(none)"
    tools_str = ", ".join(tools) if tools else "None"
    base = f"""You are **{name}** ({mode}).

INSTRUCTIONS:
{instructions_blob}

TOOLS: {tools_str}"""
    if prompt_override and prompt_override.strip():
        return base + "\n\n" + prompt_override.strip()
    return base


def build_optimized_prompt(config: AgentConfig, analysis: dict[str, Any]) -> str:
    """Build final optimized system prompt from config and analysis."""
    instructions_blob = "\n".join(f"- {i}" for i in config.instructions)
    tools_str = ", ".join(config.tools) if config.tools else "None"
    return f"""You are **{config.name}** ({config.mode}).

INSTRUCTIONS:
{instructions_blob}

TOOLS: {tools_str}

{ANALYSIS_V5_TEMPLATE}

ANALYSIS: {json.dumps(analysis)}"""
