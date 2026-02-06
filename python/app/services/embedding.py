"""Singleton embedding model (BAAI/bge-base-en-v1.5) for RAG."""

from sentence_transformers import SentenceTransformer

_embedding_model: SentenceTransformer | None = None

EMBEDDING_MODEL_ID = "BAAI/bge-base-en-v1.5"


def get_embedding_model() -> SentenceTransformer | None:
    return _embedding_model


def init_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        print("🔄 Loading BAAI/bge-base-en-v1.5...")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_ID)
        print("✅ Embedding ready")
    return _embedding_model
