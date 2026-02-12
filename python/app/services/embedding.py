"""Singleton embedding model (BAAI/bge-base-en-v1.5) for RAG."""

import logging
import os
from pathlib import Path

# Set HuggingFace cache BEFORE any hf imports to avoid G:\ and other missing-drive errors on Windows.
# Must run before sentence_transformers import.
def _ensure_hf_cache_path() -> None:
    """Use a valid HuggingFace cache path; avoid missing drives (e.g. G:\\) on Windows."""
    _vars = ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE")

    def _path_valid(p: str) -> bool:
        if not p or not p.strip():
            return False
        try:
            return Path(p).exists()
        except OSError:
            return False

    needs_fix = False
    for var in _vars:
        val = os.environ.get(var, "").strip()
        if not val or not _path_valid(val):
            needs_fix = True
            break

    if not needs_fix:
        return

    # Use project-local cache (python/.cache/huggingface) - avoids Path.home() on G:\ etc.
    _python_dir = Path(__file__).resolve().parent.parent.parent
    fallback = _python_dir / ".cache" / "huggingface"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except OSError:
        fallback = Path(os.environ.get("TEMP", os.environ.get("TMP", "/tmp"))) / "huggingface_cache"
        fallback.mkdir(parents=True, exist_ok=True)

    for var in _vars:
        val = os.environ.get(var, "").strip()
        if not val or not _path_valid(val):
            os.environ[var] = str(fallback)


_ensure_hf_cache_path()

from sentence_transformers import SentenceTransformer

# Silence sentence_transformers loggers in API
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers.SentenceTransformer").setLevel(logging.WARNING)

_embedding_model: SentenceTransformer | None = None

EMBEDDING_MODEL_ID = "BAAI/bge-base-en-v1.5"
EMBEDDING_MODEL_FALLBACK = "sentence-transformers/all-mpnet-base-v2"  # 768 dim, well-supported


def get_embedding_model() -> SentenceTransformer | None:
    return _embedding_model


def init_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        for model_id in (EMBEDDING_MODEL_ID, EMBEDDING_MODEL_FALLBACK):
            try:
                print(f"🔄 Loading {model_id}...")
                _embedding_model = SentenceTransformer(model_id)
                print("✅ Embedding ready")
                break
            except Exception as e:
                if model_id == EMBEDDING_MODEL_FALLBACK:
                    raise
                logging.getLogger(__name__).warning(
                    "BGE model failed (%s), falling back to %s: %s",
                    model_id,
                    EMBEDDING_MODEL_FALLBACK,
                    e,
                )
    return _embedding_model
