"""LLM provider protocol: router (needs_rag, tools, model) + streaming generator + prompt helpers."""

from collections.abc import Generator
from typing import Any, Protocol

from app.schemas.requests import AgentConfig


class LLMProvider(Protocol):
    """Single backend for router + generator + prompt building. Implementations: gemini, openai."""

    def run_cheap_router(
        self,
        agent_name: str,
        tools_list: str,
        query: str,
        connections_list: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return {needs_rag, tools_needed, connections_needed, model_to_use, reason}. Used before RAG and generator."""
        ...

    def run_generator_stream(
        self,
        full_prompt: str,
        generator_model_name: str,
        tool_decision: dict[str, Any],
        input_chars: int,
        docs_count: int,
        total_docs: int,
    ) -> Generator[str, None, None]:
        """Yield NDJSON lines: {text}, then final {is_final, metrics}."""
        ...

    def build_system_prompt_from_agent(
        self,
        name: str,
        mode: str,
        instructions: list[str],
        tools: list[str],
        prompt_override: str | None = None,
    ) -> str:
        """Build system prompt string from agent fields (for chat)."""
        ...

    def optimize_agent_prompt(self, config: AgentConfig) -> tuple[str, dict[str, Any]]:
        """Run analysis and return (optimized_prompt, analysis dict). Used by prompt worker."""
        ...
