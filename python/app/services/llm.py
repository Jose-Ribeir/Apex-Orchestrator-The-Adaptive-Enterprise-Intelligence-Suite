"""
LLM: provider-agnostic facade. Dispatches to Gemini or OpenAI based on LLM_PROVIDER.
Google integration remains in gemini_router; alternative in providers.llm.openai.
"""

from app.providers.llm import get_llm_provider


def run_cheap_router(
    agent_name: str,
    tools_list: str,
    query: str,
    connections_list: list[str] | None = None,
):
    return get_llm_provider().run_cheap_router(agent_name, tools_list, query, connections_list=connections_list)


def run_generator_stream(
    full_prompt: str,
    generator_model_name: str,
    tool_decision: dict,
    input_chars: int,
    docs_count: int,
    total_docs: int,
    attachments: list[dict[str, str]] | None = None,
):
    return get_llm_provider().run_generator_stream(
        full_prompt,
        generator_model_name,
        tool_decision,
        input_chars,
        docs_count,
        total_docs,
        attachments=attachments,
    )


def build_system_prompt_from_agent(
    name: str,
    mode: str,
    instructions: list[str],
    tools: list[str],
    prompt_override: str | None = None,
) -> str:
    return get_llm_provider().build_system_prompt_from_agent(name, mode, instructions, tools, prompt_override)


def optimize_agent_prompt(config):
    return get_llm_provider().optimize_agent_prompt(config)


__all__ = [
    "run_cheap_router",
    "run_generator_stream",
    "build_system_prompt_from_agent",
    "optimize_agent_prompt",
]
