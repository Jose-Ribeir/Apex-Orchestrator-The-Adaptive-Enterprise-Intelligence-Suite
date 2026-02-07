"""
Application configuration loaded from environment variables.
Use .env file or export variables; see .env.dist for required keys.
All Google backends (GCS, Vertex RAG) are required; no local fallback.
"""

from functools import lru_cache

from pydantic import field_validator
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

    # Required: Gemini (chat/router)
    gemini_api_key: str

    # Required: Google Cloud (no local fallback)
    gcp_project_id: str = ""
    gcs_bucket_name: str = ""
    gcs_documents_prefix: str = "agents"
    vertex_region: str = ""
    vertex_rag_index_endpoint_id: str = ""
    vertex_rag_index_id: str = ""
    vertex_rag_deployed_index_id: str = ""

    # Database: single URL for dev (local Postgres) and prod (Cloud SQL)
    database_url: str = ""

    # Optional with defaults
    geminimesh_api_url: str = "http://localhost:4200"
    geminimesh_api_token: str | None = None
    geminimesh_request_timeout: int = 90
    host: str = "127.0.0.1"
    port: int = 8000

    @field_validator("gemini_api_key")
    @classmethod
    def gemini_key_non_empty(cls, v: str) -> str:
        return _non_empty(v, "GEMINI_API_KEY")

    @field_validator("gcp_project_id")
    @classmethod
    def gcp_project_non_empty(cls, v: str) -> str:
        return _non_empty(v, "GCP_PROJECT_ID")

    @field_validator("gcs_bucket_name")
    @classmethod
    def gcs_bucket_non_empty(cls, v: str) -> str:
        return _non_empty(v, "GCS_BUCKET_NAME")

    @field_validator("vertex_region")
    @classmethod
    def vertex_region_non_empty(cls, v: str) -> str:
        return _non_empty(v, "VERTEX_REGION")

    @field_validator("vertex_rag_index_endpoint_id")
    @classmethod
    def vertex_rag_index_endpoint_non_empty(cls, v: str) -> str:
        return _non_empty(v, "VERTEX_RAG_INDEX_ENDPOINT_ID")

    @field_validator("vertex_rag_index_id")
    @classmethod
    def vertex_rag_index_id_non_empty(cls, v: str) -> str:
        return _non_empty(v, "VERTEX_RAG_INDEX_ID")

    @field_validator("vertex_rag_deployed_index_id")
    @classmethod
    def vertex_rag_deployed_index_id_non_empty(cls, v: str) -> str:
        return _non_empty(v, "VERTEX_RAG_DEPLOYED_INDEX_ID")

    @property
    def geminimesh_configured(self) -> bool:
        return bool(self.geminimesh_api_token)

    @property
    def database_configured(self) -> bool:
        """True if DATABASE_URL is set."""
        return bool(self.database_url.strip())

    def get_database_url(self) -> str:
        """PostgreSQL URL from DATABASE_URL."""
        if not self.database_url.strip():
            raise ValueError("Database not configured. Set DATABASE_URL in .env")
        return self.database_url.strip()


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (env read once)."""
    return Settings()
