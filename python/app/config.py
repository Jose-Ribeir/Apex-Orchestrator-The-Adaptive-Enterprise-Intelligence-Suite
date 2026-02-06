"""
Application configuration loaded from environment variables.
Use .env file or export variables; see .env.example for required keys.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-based settings. Validates on load."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required
    gemini_api_key: str

    # Optional with defaults
    geminimesh_api_url: str = "http://localhost:4200"
    geminimesh_api_token: str | None = None
    geminimesh_request_timeout: int = 90
    host: str = "127.0.0.1"
    port: int = 8000
    data_folder: str = "data"

    @field_validator("gemini_api_key")
    @classmethod
    def gemini_key_non_empty(cls, v: str) -> str:
        if not (v and v.strip()):
            raise ValueError("GEMINI_API_KEY must be set and non-empty")
        return v.strip()

    @property
    def geminimesh_configured(self) -> bool:
        return bool(self.geminimesh_api_token)


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance (env read once)."""
    return Settings()
