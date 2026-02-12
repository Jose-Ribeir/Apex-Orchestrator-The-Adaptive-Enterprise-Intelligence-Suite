"""
Application configuration loaded from environment variables.
Use .env file or export variables; see .env.dist for required keys.
Provider backends (RAG, LLM, storage) are selectable; Google is optional when using alternatives.
"""

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _non_empty(v: str, name: str) -> str:
    if not (v and str(v).strip()):
        raise ValueError(f"{name} must be set and non-empty")
    return str(v).strip()


class Settings(BaseSettings):
    """Environment-based settings. Validates on load."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Provider selection (defaults keep current Google-only behaviour) ---
    rag_provider: str = "vertex"  # vertex | memory | pgvector | lancedb
    llm_provider: str = "gemini"  # gemini | openai | groq
    storage_provider: str = "gcs"  # gcs | local | minio

    # pgvector (required when rag_provider=pgvector): uses DATABASE_URL; table and dim are optional
    rag_pgvector_table: str = "rag_embeddings"
    rag_embedding_dim: int = 768  # must match embedding model (e.g. BAAI/bge-base-en-v1.5)

    # lancedb (when rag_provider=lancedb): local path for embedded DB; no server required
    rag_lancedb_path: str = "data/lancedb"

    # Gemini (required when llm_provider=gemini)
    gemini_api_key: str = ""
    # Optional: comma-separated list of fallback keys (e.g. GEMINI_API_KEYS=key1,key2,key3)
    gemini_api_keys: str = ""

    # Google Cloud (required when rag_provider=vertex or storage_provider=gcs)
    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    gcs_documents_prefix: str = "agents"
    vertex_region: str = ""
    vertex_rag_index_endpoint_id: str = ""
    vertex_rag_index_id: str = ""
    vertex_rag_deployed_index_id: str = ""

    # OpenAI (required when llm_provider=openai)
    openai_api_key: str = ""

    # Groq (required when llm_provider=groq; free tier at console.groq.com)
    groq_api_key: str = ""

    # Local storage (optional; used when storage_provider=local)
    local_storage_path: str = "data/storage"

    # MinIO (required when storage_provider=minio)
    minio_endpoint: str = ""  # e.g. localhost:9000
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = ""
    minio_secure: bool = False  # True for HTTPS
    minio_prefix: str = "agents"  # object key prefix

    # Database: single URL for dev (local Postgres) and prod (Cloud SQL)
    database_url: str = ""

    # Queue (BullMQ): Redis URL; when set, ingest/add-document use queue instead of sync
    redis_url: str = ""

    # Optional with defaults
    geminimesh_api_url: str = "http://localhost:4200"
    geminimesh_api_token: str | None = None
    geminimesh_request_timeout: int = 90
    host: str = "127.0.0.1"
    port: int = 8000

    # Auth
    secret_key: str = "change-me-in-production"
    cookie_name: str = "session_token"
    cookie_max_age_seconds: int = 60 * 60 * 24 * 7  # 7 days
    cookie_same_site: str = "lax"  # use "none" for cross-origin + secure

    # CORS: explicit origins required when credentials=True (cannot use *)
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Google OAuth (optional; for Connections / Gmail integration)
    google_oauth_client_id: str = ""
    google_oauth_client_secret: str = ""
    app_frontend_url: str = "http://localhost:5173"  # redirect after OAuth callback

    @field_validator("gemini_api_key")
    @classmethod
    def gemini_key_optional(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("gcp_project_id", "gcs_bucket_name", "vertex_region")
    @classmethod
    def gcp_optional(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("vertex_rag_index_endpoint_id", "vertex_rag_index_id", "vertex_rag_deployed_index_id")
    @classmethod
    def vertex_optional(cls, v: str) -> str:
        return (v or "").strip()

    @model_validator(mode="after")
    def require_provider_specific_settings(self) -> "Settings":
        rp = (self.rag_provider or "vertex").strip().lower()
        lp = (self.llm_provider or "gemini").strip().lower()
        sp = (self.storage_provider or "gcs").strip().lower()

        if lp == "gemini":
            keys = self.get_gemini_api_keys()
            if not keys:
                raise ValueError("GEMINI_API_KEY or GEMINI_API_KEYS is required when LLM_PROVIDER=gemini")

        if lp == "openai" and not (self.openai_api_key and self.openai_api_key.strip()):
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        if lp == "groq" and not (self.groq_api_key and self.groq_api_key.strip()):
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

        if rp == "vertex":
            for name, val in [
                ("GCP_PROJECT_ID", self.gcp_project_id),
                ("GCS_BUCKET_NAME", self.gcs_bucket_name),
                ("VERTEX_REGION", self.vertex_region),
                ("VERTEX_RAG_INDEX_ENDPOINT_ID", self.vertex_rag_index_endpoint_id),
                ("VERTEX_RAG_INDEX_ID", self.vertex_rag_index_id),
                ("VERTEX_RAG_DEPLOYED_INDEX_ID", self.vertex_rag_deployed_index_id),
            ]:
                if not (val and str(val).strip()):
                    raise ValueError(f"{name} is required when RAG_PROVIDER=vertex")

        if rp == "pgvector":
            if not self.database_url or not self.database_url.strip():
                raise ValueError("DATABASE_URL is required when RAG_PROVIDER=pgvector")

        if rp == "lancedb":
            if not (self.rag_lancedb_path and self.rag_lancedb_path.strip()):
                raise ValueError("RAG_LANCEDB_PATH must be set when RAG_PROVIDER=lancedb")

        if sp == "gcs":
            for name, val in [
                ("GCP_PROJECT_ID", self.gcp_project_id),
                ("GCS_BUCKET_NAME", self.gcs_bucket_name),
            ]:
                if not (val and str(val).strip()):
                    raise ValueError(f"{name} is required when STORAGE_PROVIDER=gcs")

        if sp == "minio":
            for name, val in [
                ("MINIO_ENDPOINT", self.minio_endpoint),
                ("MINIO_ACCESS_KEY", self.minio_access_key),
                ("MINIO_SECRET_KEY", self.minio_secret_key),
                ("MINIO_BUCKET", self.minio_bucket),
            ]:
                if not (val and str(val).strip()):
                    raise ValueError(f"{name} is required when STORAGE_PROVIDER=minio")

        return self

    def get_gemini_api_keys(self) -> list[str]:
        """Return list of Gemini API keys from GEMINI_API_KEYS or GEMINI_API_KEY (both support comma-separated)."""
        keys_str = (self.gemini_api_keys or "").strip()
        if keys_str:
            return [k.strip() for k in keys_str.split(",") if k.strip()]
        key = (self.gemini_api_key or "").strip()
        if key:
            if "," in key:
                return [k.strip() for k in key.split(",") if k.strip()]
            return [key]
        return []

    @property
    def geminimesh_configured(self) -> bool:
        return bool(self.geminimesh_api_token)

    @property
    def database_configured(self) -> bool:
        """True if DATABASE_URL is set."""
        return bool(self.database_url.strip())

    @property
    def queue_configured(self) -> bool:
        """True if REDIS_URL is set (queue enabled for indexing jobs)."""
        return bool(self.redis_url.strip())

    def get_database_url(self) -> str:
        """PostgreSQL URL from DATABASE_URL. Normalizes postgres:// to postgresql:// for SQLAlchemy."""
        url = self.database_url.strip()
        if not url:
            raise ValueError("Database not configured. Set DATABASE_URL in .env")
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (env read once)."""
    return Settings()
