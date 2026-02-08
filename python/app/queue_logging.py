"""Structured logging for the queue system (enqueue, worker start/complete/fail/retry)."""

import json
import logging
from typing import Any

logger = logging.getLogger("app.queue")


def _extra(
    job_id: str,
    agent_id: str,
    job_type: str,
    event: str,
    *,
    duration_ms: int | None = None,
    error: str | None = None,
    documents_count: int | None = None,
    attempt: int | None = None,
    queue_name: str = "agent-indexing",
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "job_id": job_id,
        "agent_id": agent_id,
        "job_type": job_type,
        "event": event,
        "queue_name": queue_name,
    }
    if duration_ms is not None:
        out["duration_ms"] = duration_ms
    if error is not None:
        out["error"] = error
    if documents_count is not None:
        out["documents_count"] = documents_count
    if attempt is not None:
        out["attempt"] = attempt
    return out


def log_queue_event(
    job_id: str,
    agent_id: str,
    job_type: str,
    event: str,
    *,
    duration_ms: int | None = None,
    error: str | None = None,
    documents_count: int | None = None,
    attempt: int | None = None,
    queue_name: str = "agent-indexing",
) -> None:
    """Emit one structured log line for queue lifecycle. event: enqueued | started | completed | failed | retrying."""
    extra_dict = _extra(
        job_id=job_id,
        agent_id=agent_id,
        job_type=job_type,
        event=event,
        duration_ms=duration_ms,
        error=error,
        documents_count=documents_count,
        attempt=attempt,
        queue_name=queue_name,
    )
    msg = json.dumps(extra_dict)
    if event == "failed":
        logger.error(msg, extra=extra_dict)
    elif event == "retrying":
        logger.warning(msg, extra=extra_dict)
    else:
        logger.info(msg, extra=extra_dict)
