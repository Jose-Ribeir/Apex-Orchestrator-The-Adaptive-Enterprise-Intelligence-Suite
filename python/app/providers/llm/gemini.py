"""Gemini LLM provider: delegates to existing gemini_router (Google)."""


class GeminiLLMProvider:
    """LLM provider using Google Gemini (router + generator)."""

    def run_cheap_router(
        self,
        agent_name: str,
        tools_list: str,
        query: str,
        connections_list: list[str] | None = None,
    ):
        from app.services import gemini_router

        return gemini_router.run_cheap_router(agent_name, tools_list, query, connections_list=connections_list)

    def run_generator_stream(
        self,
        full_prompt: str,
        generator_model_name: str,
        tool_decision: dict,
        input_chars: int,
        docs_count: int,
        total_docs: int,
    ):
        from app.services import gemini_router

        return gemini_router.run_generator_stream(
            full_prompt,
            generator_model_name,
            tool_decision,
            input_chars,
            docs_count,
            total_docs,
        )

    def build_system_prompt_from_agent(
        self,
        name: str,
        mode: str,
        instructions: list[str],
        tools: list[str],
        prompt_override: str | None = None,
    ) -> str:
        from app.services import gemini_router

        return gemini_router.build_system_prompt_from_agent(name, mode, instructions, tools, prompt_override)

    def optimize_agent_prompt(self, config):
        from app.services import gemini_router

        return gemini_router.optimize_agent_prompt(config)
