"""LLM providers: Gemini (Google), Groq, or OpenAI. Selected via LLM_PROVIDER env."""

from app.config import get_settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider
from app.providers.llm.groq import GroqLLMProvider
from app.providers.llm.openai import OpenAILLMProvider

_PROVIDER: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider (gemini | groq | openai). Cached per process."""
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    lp = (get_settings().llm_provider or "gemini").strip().lower()
    if lp == "groq":
        _PROVIDER = GroqLLMProvider()
    elif lp == "openai":
        _PROVIDER = OpenAILLMProvider()
    else:
        _PROVIDER = GeminiLLMProvider()
    return _PROVIDER


__all__ = [
    "LLMProvider",
    "get_llm_provider",
    "GeminiLLMProvider",
    "GroqLLMProvider",
    "OpenAILLMProvider",
]
