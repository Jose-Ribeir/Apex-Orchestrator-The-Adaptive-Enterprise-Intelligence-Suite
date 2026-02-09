"""MinIO (S3-compatible) storage provider: self-hosted object storage."""

from __future__ import annotations

from datetime import timedelta
from io import BytesIO

from app.config import get_settings
from app.providers.storage.base import StorageProvider

# URI format: s3://bucket/key (S3-compatible convention for MinIO)


def _get_client():
    from minio import Minio

    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def _ensure_bucket(client, bucket: str) -> None:
    """Create the bucket if it does not exist (idempotent)."""
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
    except Exception:
        raise


class MinIOStorageProvider(StorageProvider):
    """Storage using MinIO (S3-compatible). URI format: s3://bucket/key."""

    def upload(
        self,
        agent_name: str,
        file_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        settings = get_settings()
        bucket = settings.minio_bucket
        prefix = (getattr(settings, "minio_prefix", None) or "agents").strip("/")
        object_name = f"{prefix}/{agent_name}/documents/{file_key}"
        client = _get_client()
        _ensure_bucket(client, bucket)
        client.put_object(
            bucket,
            object_name,
            BytesIO(content),
            len(content),
            content_type=content_type,
        )
        return f"s3://{bucket}/{object_name}"

    def generate_signed_url(self, uri: str, expiration_seconds: int = 3600) -> str | None:
        if not uri or not uri.startswith("s3://"):
            return None
        # s3://bucket/key
        path = uri[5:]  # strip s3://
        parts = path.split("/", 1)
        if len(parts) != 2:
            return None
        bucket_name, object_name = parts
        try:
            client = _get_client()
            return client.presigned_get_object(
                bucket_name,
                object_name,
                expires=timedelta(seconds=expiration_seconds),
            )
        except Exception:
            return None
