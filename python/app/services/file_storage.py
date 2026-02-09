"""
Storage: provider-agnostic facade. Dispatches to GCS or local based on STORAGE_PROVIDER.
Google integration remains in providers.storage.gcs; alternative in providers.storage.local.
"""

from app.providers.storage import get_storage_provider


def upload(
    agent_name: str,
    file_key: str,
    content: bytes,
    content_type: str,
) -> str:
    """Upload file; return URI (gs:// or file:// per STORAGE_PROVIDER)."""
    return get_storage_provider().upload(agent_name, file_key, content, content_type)


def generate_signed_url(uri: str, expiration_seconds: int = 3600) -> str | None:
    """Generate time-limited URL for the given URI. Returns None if not supported."""
    return get_storage_provider().generate_signed_url(uri, expiration_seconds)
