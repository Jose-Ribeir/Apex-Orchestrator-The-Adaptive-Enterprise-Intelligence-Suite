"""Google Cloud Storage for raw uploaded documents. GCS only; no local fallback."""

from datetime import timedelta

from app.config import get_settings


def _client():
    from google.cloud import storage

    settings = get_settings()
    return storage.Client(project=settings.gcp_project_id)


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
    settings = get_settings()
    client = _client()
    bucket = client.bucket(settings.gcs_bucket_name)
    prefix = (settings.gcs_documents_prefix or "agents").strip("/")
    blob_path = f"{prefix}/{agent_name}/documents/{file_key}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(
        content,
        content_type=content_type,
    )
    return f"gs://{settings.gcs_bucket_name}/{blob_path}"


def generate_signed_url(gs_uri: str, expiration_seconds: int = 3600) -> str | None:
    """
    Generate a time-limited authenticated (signed) URL for a GCS object.
    Returns None if gs_uri is invalid or signing fails.
    """
    if not gs_uri or not gs_uri.startswith("gs://"):
        return None
    # gs://bucket/path/to/object -> bucket, path/to/object
    parts = gs_uri[5:].split("/", 1)  # strip "gs://"
    if len(parts) != 2:
        return None
    bucket_name, blob_path = parts
    try:
        client = _client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        url = blob.generate_signed_url(
            expiration=timedelta(seconds=expiration_seconds),
            method="GET",
        )
        return url
    except Exception:
        return None
