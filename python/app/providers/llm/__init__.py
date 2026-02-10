"""LLM providers: Google Gemini only (Gemini 3 models)."""

from app.providers.llm.base import LLMProvider
from app.providers.llm.gemini import GeminiLLMProvider

_PROVIDER: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    """Return the Gemini LLM provider (Google only; Gemini 3 models). Cached per process."""
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    _PROVIDER = GeminiLLMProvider()
    return _PROVIDER


__all__ = [
    "LLMProvider",
    "get_llm_provider",
    "GeminiLLMProvider",
]
