"""GeminiMesh API client: push optimized prompt via POST /agents/{id}/prompt (no sync loop)."""

import logging
from typing import Any

import requests

from app.config import get_settings

logger = logging.getLogger("app.geminimesh")


def update_agent_in_geminimesh(
    agent_id: str,
    name: str,
    prompt: str | None,
) -> dict[str, Any]:
    """
    POST GeminiMesh /agents/{id}/prompt with prompt only.
    Does not trigger sync back to Python. Returns parsed JSON; raises on non-2xx.
    """
    settings = get_settings()
    if not settings.geminimesh_api_token:
        raise ValueError("GEMINIMESH_API_TOKEN not configured")

    url = f"{settings.geminimesh_api_url.rstrip('/')}/agents/{agent_id}/prompt"
    headers = {"Content-Type": "application/json"}
    if settings.geminimesh_api_token:
        headers["Authorization"] = f"Bearer {settings.geminimesh_api_token}"
    payload = {"prompt": prompt}
    timeout = settings.geminimesh_request_timeout
    logger.info("POST %s agent_id=%s name=%s timeout=%s", url, agent_id, name, timeout)
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code not in (200, 201, 202):
        logger.error(
            "GeminiMesh API error agent_id=%s status=%s body=%s",
            agent_id,
            resp.status_code,
            resp.text[:500] if resp.text else "(empty)",
        )
        err = requests.HTTPError(f"GeminiMesh API error: {resp.status_code} - {resp.text}")
        err.response = resp
        raise err
    logger.info(
        "GeminiMesh POST prompt success agent_id=%s status=%s",
        agent_id,
        resp.status_code,
    )
    return resp.json()
