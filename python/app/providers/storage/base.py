"""Storage provider protocol: upload raw files and generate signed URLs."""


class StorageProvider:
    """Abstract storage: upload returns a URI (gs:// or file://); signed URL for download."""

    def upload(
        self,
        agent_name: str,
        file_key: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Store content; return URI (e.g. gs://bucket/path or file:///abs/path)."""
        ...

    def generate_signed_url(self, uri: str, expiration_seconds: int = 3600) -> str | None:
        """Return a time-limited URL for the given URI, or None if not supported."""
        ...
