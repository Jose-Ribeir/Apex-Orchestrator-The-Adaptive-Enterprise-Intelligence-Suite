"""GCS storage provider: delegates to GCS implementation (avoid circular import)."""

from app.providers.storage.base import StorageProvider


def _gcs_upload(agent_name: str, file_key: str, content: bytes, content_type: str) -> str:
    from google.cloud import storage

    from app.config import get_settings

    settings = get_settings()
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket_name)
    prefix = (settings.gcs_documents_prefix or "agents").strip("/")
    blob_path = f"{prefix}/{agent_name}/documents/{file_key}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(content, content_type=content_type)
    return f"gs://{settings.gcs_bucket_name}/{blob_path}"


def _gcs_signed_url(uri: str, expiration_seconds: int = 3600) -> str | None:
    if not uri or not uri.startswith("gs://"):
        return None
    from datetime import timedelta

    from google.cloud import storage

    from app.config import get_settings

    parts = uri[5:].split("/", 1)
    if len(parts) != 2:
        return None
    bucket_name, blob_path = parts
    try:
        client = storage.Client(project=get_settings().gcp_project_id)
        blob = client.bucket(bucket_name).blob(blob_path)
        return blob.generate_signed_url(expiration=timedelta(seconds=expiration_seconds), method="GET")
    except Exception:
        return None


class GCSStorageProvider(StorageProvider):
    """Storage using Google Cloud Storage."""

    def upload(
        self,
        agent_name: str,
        file_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        return _gcs_upload(agent_name, file_key, content, content_type)

    def generate_signed_url(self, uri: str, expiration_seconds: int = 3600) -> str | None:
        return _gcs_signed_url(uri, expiration_seconds)
