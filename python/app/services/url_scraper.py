"""Fetch URL, extract main content (ignore nav/ads), and chunk for RAG."""

import logging
import re
import time
from urllib.parse import urlparse

import requests

from app.services.document_parser import _chunk_text

logger = logging.getLogger(__name__)

# Max URL length and fetch timeout
MAX_URL_LENGTH = 2048
FETCH_TIMEOUT_SECONDS = 30


def _normalize_url(url: str) -> str:
    """Strip whitespace and ensure scheme."""
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


def _validate_url(url: str) -> None:
    """Raise ValueError if URL is invalid (scheme, host, length)."""
    if not url or len(url) > MAX_URL_LENGTH:
        raise ValueError(f"URL must be 1–{MAX_URL_LENGTH} characters")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https")
    if not parsed.netloc or not parsed.netloc.split(".")[0]:
        raise ValueError("URL must have a valid host")


def url_to_docs(url: str) -> tuple[list[dict], str]:
    """
    Fetch URL, extract main content with trafilatura, chunk for RAG.
    Returns (list of {id, content, metadata}, page_title_or_url).
    Raises ValueError on invalid URL or empty extraction.
    """
    url = _normalize_url(url)
    _validate_url(url)

    import trafilatura

    resp = requests.get(url, timeout=FETCH_TIMEOUT_SECONDS)
    resp.raise_for_status()
    html = resp.text
    if not html or not html.strip():
        raise ValueError("Failed to fetch URL (empty response)")

    result = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_links=False,
        output_format="txt",
    )
    if not result or not result.strip():
        raise ValueError("No main content could be extracted from this page")

    text = result.strip()
    # Sanitize source_id for chunk ids
    parsed = urlparse(url)
    domain = re.sub(r"[^\w\-.]", "_", parsed.netloc or "url")[:64]
    source_id = f"url_{domain}_{int(time.time())}"
    docs = _chunk_text(text, source_id, source_file_uri=None)
    for d in docs:
        d["metadata"] = d.get("metadata") or {}
        d["metadata"]["source_url"] = url

    # Title: trafilatura can extract metadata from the HTML
    meta = trafilatura.extract_metadata(html, default_url=url)
    title = (meta and meta.title) or url
    if len(title) > 512:
        title = title[:509] + "..."

    return docs, title
