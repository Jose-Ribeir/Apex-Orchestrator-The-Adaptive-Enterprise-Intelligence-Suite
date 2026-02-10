"""Singleton embedding model (BAAI/bge-base-en-v1.5) for RAG."""

import os
from pathlib import Path

from sentence_transformers import SentenceTransformer

_embedding_model: SentenceTransformer | None = None

EMBEDDING_MODEL_ID = "BAAI/bge-base-en-v1.5"


def _ensure_hf_cache_path() -> None:
    """Use a valid HuggingFace cache path; avoid missing drives (e.g. G:\\) on Windows."""
    fallback = Path.home() / ".cache" / "huggingface"
    vars_ = ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE")
    need_fallback = False
    for var in vars_:
        val = os.environ.get(var)
        if not val:
            need_fallback = True
            break
        try:
            if len(val) >= 2 and val[1] == ":" and not Path(val).exists():
                need_fallback = True
                break
        except OSError:
            need_fallback = True
            break
    if need_fallback:
        fallback.mkdir(parents=True, exist_ok=True)
        for var in vars_:
            val = os.environ.get(var)
            try:
                if not val or not Path(val).exists():
                    os.environ[var] = str(fallback)
            except OSError:
                os.environ[var] = str(fallback)


def get_embedding_model() -> SentenceTransformer | None:
    return _embedding_model


def init_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _ensure_hf_cache_path()
        print("🔄 Loading BAAI/bge-base-en-v1.5...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_ID)
        print("✅ Embedding ready")
    return _embedding_model
