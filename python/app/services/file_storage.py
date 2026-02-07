"""Google Cloud Storage for raw uploaded documents. GCS only; no local fallback."""

from app.config import get_settings


def upload(
    agent_name: str,
    file_key: str,
    content: bytes,
    content_type: str,
) -> str:
    """
    Upload file content to GCS. Returns the gs:// URI.
    Path: {gcs_documents_prefix}/{agent_name}/documents/{file_key}
    """
    from google.cloud import storage

    settings = get_settings()
    client = storage.Client(project=settings.gcp_project_id)
    bucket = client.bucket(settings.gcs_bucket_name)
    prefix = (settings.gcs_documents_prefix or "agents").strip("/")
    blob_path = f"{prefix}/{agent_name}/documents/{file_key}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        content,
        content_type=content_type,
    )
    return f"gs://{settings.gcs_bucket_name}/{blob_path}"
