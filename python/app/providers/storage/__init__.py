"""Storage providers: gcs (Google Cloud Storage), local (filesystem), minio (S3-compatible)."""

from app.config import get_settings
from app.providers.storage.base import StorageProvider
from app.providers.storage.gcs import GCSStorageProvider
from app.providers.storage.local import LocalStorageProvider
from app.providers.storage.minio import MinIOStorageProvider

_PROVIDER: StorageProvider | None = None


def get_storage_provider() -> StorageProvider:
    """Return the configured storage provider (gcs | local | minio). Cached per process."""
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER
    settings = get_settings()
    name = (settings.storage_provider or "gcs").strip().lower()
    if name == "local":
        _PROVIDER = LocalStorageProvider()
    elif name == "minio":
        _PROVIDER = MinIOStorageProvider()
    else:
        _PROVIDER = GCSStorageProvider()
    return _PROVIDER


__all__ = [
    "StorageProvider",
    "get_storage_provider",
    "GCSStorageProvider",
    "LocalStorageProvider",
    "MinIOStorageProvider",
]
