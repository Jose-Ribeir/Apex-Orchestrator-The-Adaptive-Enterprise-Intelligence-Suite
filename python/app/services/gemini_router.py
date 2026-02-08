"""Gemini 2-call pipeline: cheap router (flash-lite) + dynamic generator."""

import json
from collections.abc import Generator
from typing import Any

from google import genai

from app.config import get_settings
from app.schemas.requests import AgentConfig

ANALYSIS_V5_TEMPLATE = """
--- ROUTING LOGIC (V5) ---
Classify into Profile 1 (RETRIEVAL '1-Yes') or Profile 2 (DIRECT '2-No').
Rule: If doubt, choose '1-Yes'. Reply ONLY '1-Yes' or '2-No'.
"""

CHEAP_ROUTER_TEMPLATE = """
CHEAP ROUTER (gemini-2.5-flash-lite) - 50 tokens max:

AGENT: {agent_name}
TOOLS: {tools_list}
QUERY: "{query}"

JSON ONLY:
{{
  "needs_rag": true/false,
  "tools_needed": ["RAG"]|["RAG","Calculator"]|[],
  "model_to_use": "gemini-3-pro-preview"|"gemini-3-flash-preview"|"gemini-2.5-flash",
  "reason": "1-sentence"
}}
"""

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def run_cheap_router(agent_name: str, tools_list: str, query: str) -> dict[str, Any]:
    """Call gemini-2.5-flash-lite to get needs_rag, tools_needed, model_to_use."""
    client = _get_client()
    prompt = CHEAP_ROUTER_TEMPLATE.format(
        agent_name=agent_name,
        tools_list=tools_list,
        query=query,
    )
    resp = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt,
    )
    try:
        return json.loads(resp.text.strip())
    except (json.JSONDecodeError, AttributeError):
        return {
            "needs_rag": True,
            "tools_needed": ["RAG"],
            "model_to_use": "gemini-2.5-flash",
            "reason": "fallback",
        }


def _resolve_generator_model(model_name: str) -> str:
    """Return model name; fallback to gemini-2.5-flash if invalid."""
    return model_name or "gemini-2.5-flash"


def run_generator_stream(
    full_prompt: str,
    generator_model_name: str,
    tool_decision: dict[str, Any],
    input_chars: int,
    docs_count: int,
    total_docs: int,
) -> Generator[str, None, None]:
    """Stream generator model response; yields NDJSON lines."""
    client = _get_client()
    model_name = _resolve_generator_model(generator_model_name)
    output_chars = 0
    output_tokens = 0

    try:
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=full_prompt,
        )
    except Exception:
        model_name = "gemini-2.5-flash"
        stream = client.models.generate_content_stream(
            model=model_name,
            contents=full_prompt,
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
                    "router_model": "gemini-2.5-flash-lite",
                    "generator_model": model_name,
                    "tools_used": tool_decision.get("tools_needed", []),
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
        model="gemini-3-pro-preview",
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
