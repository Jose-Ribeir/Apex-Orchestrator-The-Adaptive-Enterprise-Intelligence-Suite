"""LLM providers: gemini (Google), openai (OpenAI), groq (Groq)."""

from app.config import get_settings
from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider
from app.providers.llm.groq import GroqLLMProvider
from app.providers.llm.openai import OpenAILLMProvider

_PROVIDER: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Return the configured LLM provider (gemini | openai | groq). Cached per process."""
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    settings = get_settings()
    name = (settings.llm_provider or "gemini").strip().lower()
    if name == "openai":
        _PROVIDER = OpenAILLMProvider()
    elif name == "groq":
        _PROVIDER = GroqLLMProvider()
    else:
        _PROVIDER = GeminiLLMProvider()
    return _PROVIDER


__all__ = [
    "LLMProvider",
    "get_llm_provider",
    "GeminiLLMProvider",
    "OpenAILLMProvider",
    "GroqLLMProvider",
]
