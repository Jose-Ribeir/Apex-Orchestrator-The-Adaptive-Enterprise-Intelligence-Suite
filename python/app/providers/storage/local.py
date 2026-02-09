"""Local filesystem storage provider: no GCP. Files under a base directory."""

from __future__ import annotations

import os
from pathlib import Path

from app.config import get_settings
from app.providers.storage.base import StorageProvider


def _base_dir() -> Path:
    settings = get_settings()
    raw = (getattr(settings, "local_storage_path", None) or "").strip() or "data/storage"
    p = Path(raw)
    if not p.is_absolute():
        p = Path.cwd() / p
    return p


class LocalStorageProvider(StorageProvider):
    """Storage using local filesystem. URI format: file:///abs/path."""

    def upload(
        self,
        agent_name: str,
        file_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        base = _base_dir()
        # agent_name may be UUID or name; sanitize for path
        safe_agent = "".join(c for c in agent_name if c.isalnum() or c in "-_") or "default"
        full = base / safe_agent / "documents" / file_key
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content)
        return f"file://{full.resolve()}"

    def generate_signed_url(self, uri: str, expiration_seconds: int = 3600) -> str | None:
        """Local: no real signing. Return file path as-is for same-server access; API can serve via /files?path=."""
        if not uri or not uri.startswith("file://"):
            return None
        path = uri[7:]  # strip file://
        if not os.path.isabs(path):
            return None
        # Caller may use this path to serve the file; we don't create a signed URL
        return path
