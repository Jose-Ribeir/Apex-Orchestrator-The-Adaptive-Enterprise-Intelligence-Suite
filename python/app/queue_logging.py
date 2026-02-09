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


def log_worker_started(queue_name: str, worker_type: str = "indexing") -> None:
    """Log when a worker process has started and is listening for jobs."""
    extra_dict: dict[str, Any] = {
        "event": "worker_started",
        "queue_name": queue_name,
        "worker_type": worker_type,
    }
    msg = json.dumps(extra_dict)
    logger.info(msg, extra=extra_dict)


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
    """Emit one structured log line for queue lifecycle.
    event: enqueued | received | processing | started | completed | failed | retrying | worker_started.
    Use job_id=agent_id='' for worker_started.
    """
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
