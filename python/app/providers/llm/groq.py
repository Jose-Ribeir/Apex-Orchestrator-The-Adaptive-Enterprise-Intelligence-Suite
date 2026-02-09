"""Groq LLM provider: router + streaming generator. Free tier, fast inference."""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any

from app.config import get_settings
from app.schemas.requests import AgentConfig

ROUTER_MODEL = "llama-3.1-8b-instant"
GENERATOR_MODEL_DEFAULT = "llama-3.3-70b-versatile"
MODEL_MAP = {
    "gemini-3-pro-preview": "llama-3.3-70b-versatile",
    "gemini-3-flash-preview": "llama-3.1-8b-instant",
    "gemini-2.5-flash": "llama-3.3-70b-versatile",
    "gemini-2.5-flash-lite": "llama-3.1-8b-instant",
}

_client: Any = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq

        _client = Groq(api_key=get_settings().groq_api_key)
    return _client


ROUTER_TEMPLATE = """AGENT: {agent_name}
TOOLS: {tools_list}
CONNECTIONS: {connections_list}
QUERY: "{query}"

Reply with JSON only:
{{"needs_rag": true/false, "tools_needed": ["RAG"] or [], "connections_needed": ["google"] or [], "model_to_use": "llama-3.3-70b-versatile" or "llama-3.1-8b-instant", "reason": "one sentence"}}
"""  # noqa: E501


class GroqLLMProvider:
    """LLM provider using Groq (fast inference, free tier)."""

    def run_cheap_router(
        self,
        agent_name: str,
        tools_list: str,
        query: str,
        connections_list: list[str] | None = None,
    ) -> dict[str, Any]:
        client = _get_client()
        connections_json = json.dumps(connections_list or [])
        prompt = ROUTER_TEMPLATE.format(
            agent_name=agent_name,
            tools_list=tools_list,
            connections_list=connections_json,
            query=query,
        )
        resp = client.chat.completions.create(
            model=ROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        text = (resp.choices[0].message.content or "").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {
                "needs_rag": True,
                "tools_needed": ["RAG"],
                "connections_needed": [],
                "model_to_use": GENERATOR_MODEL_DEFAULT,
                "reason": "parse fallback",
            }

    def run_generator_stream(
        self,
        full_prompt: str,
        generator_model_name: str,
        tool_decision: dict[str, Any],
        input_chars: int,
        docs_count: int,
        total_docs: int,
    ) -> Generator[str, None, None]:
        client = _get_client()
        model = MODEL_MAP.get(
            (generator_model_name or "").strip(),
            GENERATOR_MODEL_DEFAULT,
        )
        output_chars = 0
        output_tokens = 0
        stream = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                output_chars += len(delta)
                output_tokens += len(delta) // 4
                yield (
                    json.dumps(
                        {
                            "text": delta,
                            "metrics": {
                                "call_count": 2,
                                "input_chars": input_chars,
                                "output_chars": output_chars,
                                "input_tokens": input_chars // 4,
                                "output_tokens": output_tokens,
                                "generator_model": model,
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
                        "router_model": ROUTER_MODEL,
                        "generator_model": model,
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

    def build_system_prompt_from_agent(
        self,
        name: str,
        mode: str,
        instructions: list[str],
        tools: list[str],
        prompt_override: str | None = None,
    ) -> str:
        instructions_blob = "\n".join(f"- {i}" for i in instructions) if instructions else "(none)"
        tools_str = ", ".join(tools) if tools else "None"
        base = f"""You are **{name}** ({mode}).

INSTRUCTIONS:
{instructions_blob}

TOOLS: {tools_str}"""
        if prompt_override and prompt_override.strip():
            return base + "\n\n" + prompt_override.strip()
        return base

    def optimize_agent_prompt(self, config: AgentConfig) -> tuple[str, dict[str, Any]]:
        """Simple analysis without LLM call; returns (prompt, analysis)."""
        analysis = {
            "agent_type": "general",
            "complexity": "medium",
            "needs_rag": bool(config.tools),
        }
        instructions_blob = "\n".join(f"- {i}" for i in config.instructions)
        tools_str = ", ".join(config.tools) if config.tools else "None"
        prompt = f"""You are **{config.name}** ({config.mode}).

INSTRUCTIONS:
{instructions_blob}

TOOLS: {tools_str}

ANALYSIS: {json.dumps(analysis)}"""
        return prompt, analysis
