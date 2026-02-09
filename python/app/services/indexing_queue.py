"""Indexing queue: enqueue ingest/add-document jobs (BullMQ) and run them in worker."""

import base64
import logging
import time
import uuid

from app.config import get_settings

logger = logging.getLogger(__name__)
from app.queue_logging import log_queue_event
from app.services.agent_service import set_agent_indexing_status
from app.services.documents_service import ingest_one_file_sync, ingest_one_url_sync
from app.services.documents_service import record_documents as record_documents_svc
from app.services.rag import get_or_create_retriever

QUEUE_NAME = "agent-indexing"
ALLOWED_JOB_TYPES = ("ingest", "add", "ingest_url")

_queue = None


def _get_queue():
    """Return BullMQ Queue or None if Redis not configured. Cached."""
    global _queue
    settings = get_settings()
    if not settings.queue_configured:
        return None
    if _queue is None:
        try:
            from bullmq import Queue

            opts = {"connection": settings.redis_url.strip()}
            _queue = Queue(QUEUE_NAME, opts)
        except Exception:
            return None
    return _queue


async def enqueue_ingest(agent_id: uuid.UUID, filename: str, content_base64: str) -> str | None:
    """Enqueue an ingest job. Returns job id or None if queue unavailable."""
    q = _get_queue()
    if q is None:
        logger.warning("Queue unavailable (Redis not configured); cannot enqueue ingest for agent_id=%s", agent_id)
        return None
    agent_id_str = str(agent_id)
    try:
        job = await q.add(
            "ingest",
            {"agent_id": agent_id_str, "job_type": "ingest", "filename": filename, "content_base64": content_base64},
        )
        job_id = str(job.id) if job and getattr(job, "id", None) is not None else ""
        if job_id:
            log_queue_event(job_id, agent_id_str, "ingest", "enqueued", queue_name=QUEUE_NAME)
            logger.info("Enqueued ingest job_id=%s agent_id=%s filename=%s", job_id, agent_id_str, filename)
        return job_id
    except Exception as e:
        logger.exception("Failed to enqueue ingest agent_id=%s filename=%s: %s", agent_id_str, filename, e)
        raise


async def enqueue_ingest_url(agent_id: uuid.UUID, url: str) -> str | None:
    """Enqueue a URL ingest job. Returns job id or None if queue unavailable."""
    q = _get_queue()
    if q is None:
        logger.warning("Queue unavailable (Redis not configured); cannot enqueue ingest-url for agent_id=%s", agent_id)
        return None
    agent_id_str = str(agent_id)
    try:
        job = await q.add("ingest_url", {"agent_id": agent_id_str, "job_type": "ingest_url", "url": url})
        job_id = str(job.id) if job and getattr(job, "id", None) is not None else ""
        if job_id:
            log_queue_event(job_id, agent_id_str, "ingest_url", "enqueued", queue_name=QUEUE_NAME)
            logger.info("Enqueued ingest_url job_id=%s agent_id=%s url=%s", job_id, agent_id_str, url[:80])
        return job_id
    except Exception as e:
        logger.exception("Failed to enqueue ingest_url agent_id=%s: %s", agent_id_str, e)
        raise


async def enqueue_add_document(agent_id: uuid.UUID, document: dict) -> str | None:
    """Enqueue an add-document job. Returns job id or None if queue unavailable."""
    q = _get_queue()
    if q is None:
        logger.warning(
            "Queue unavailable (Redis not configured); cannot enqueue add-document for agent_id=%s", agent_id
        )
        return None
    agent_id_str = str(agent_id)
    try:
        job = await q.add("add", {"agent_id": agent_id_str, "job_type": "add", "document": document})
        job_id = str(job.id) if job and getattr(job, "id", None) is not None else ""
        if job_id:
            log_queue_event(job_id, agent_id_str, "add", "enqueued", queue_name=QUEUE_NAME)
            logger.info("Enqueued add-document job_id=%s agent_id=%s", job_id, agent_id_str)
        return job_id
    except Exception as e:
        logger.exception("Failed to enqueue add-document agent_id=%s: %s", agent_id_str, e)
        raise


def run_job_sync(data: dict) -> None:
    """
    Run one indexing job (ingest or add). Called from worker.
    Sets agent metadata.status.indexing to completed or error.
    Raises on failure so worker can log and retry.
    """
    agent_id_str = data.get("agent_id") or ""
    job_type = data.get("job_type") or ""
    job_id = data.get("_job_id", "")
    started = time.monotonic()

    logger.info("run_job_sync started job_id=%s agent_id=%s job_type=%s", job_id, agent_id_str, job_type)

    if not agent_id_str or job_type not in ALLOWED_JOB_TYPES:
        logger.error("Invalid job data: job_id=%s agent_id=%s job_type=%s", job_id, agent_id_str, job_type)
        set_agent_indexing_status(agent_id_str, "error", error_message="Invalid job data")
        raise ValueError(f"agent_id and job_type ({'|'.join(ALLOWED_JOB_TYPES)}) required")

    try:
        if job_type == "ingest":
            filename = data.get("filename") or ""
            content_b64 = data.get("content_base64") or ""
            if not filename or not content_b64:
                set_agent_indexing_status(agent_id_str, "error", error_message="filename and content_base64 required")
                raise ValueError("filename and content_base64 required")
            content = base64.b64decode(content_b64, validate=True)
            logger.info("Ingest decoding done job_id=%s filename=%s size_bytes=%s", job_id, filename, len(content))
            if get_settings().database_configured:
                count = ingest_one_file_sync(uuid.UUID(agent_id_str), filename, content)
                logger.info("Ingest completed job_id=%s agent_id=%s documents_count=%s", job_id, agent_id_str, count)
            else:
                logger.warning(
                    "Ingest skipped: DATABASE_URL not set in worker. RAG and DB will be empty. "
                    "Set DATABASE_URL in the worker env."
                )
                count = 0
            set_agent_indexing_status(agent_id_str, "completed")
            duration_ms = int((time.monotonic() - started) * 1000)
            log_queue_event(
                job_id,
                agent_id_str,
                "ingest",
                "completed",
                duration_ms=duration_ms,
                documents_count=count,
                queue_name=QUEUE_NAME,
            )
        elif job_type == "add":
            doc = data.get("document") or {}
            doc_id = doc.get("id") or f"doc_{int(time.time())}"
            content = (doc.get("content") or "").strip()
            if not content:
                set_agent_indexing_status(agent_id_str, "error", error_message="document.content required")
                raise ValueError("document.content required")
            doc_obj = {"id": doc_id, "content": content, "metadata": doc.get("metadata") or {}}
            logger.info("Add document job_id=%s agent_id=%s doc_id=%s", job_id, agent_id_str, doc_id)
            rag = get_or_create_retriever(agent_id_str)
            rag.add_or_update_documents([doc_obj])
            if get_settings().database_configured:
                record_documents_svc(uuid.UUID(agent_id_str), [doc_obj], source_name="", source_type="text")
            set_agent_indexing_status(agent_id_str, "completed")
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Add document completed job_id=%s agent_id=%s duration_ms=%s", job_id, agent_id_str, duration_ms
            )
            log_queue_event(
                job_id,
                agent_id_str,
                "add",
                "completed",
                duration_ms=duration_ms,
                documents_count=1,
                queue_name=QUEUE_NAME,
            )
        elif job_type == "ingest_url":
            url = (data.get("url") or "").strip()
            if not url:
                set_agent_indexing_status(agent_id_str, "error", error_message="url required")
                raise ValueError("url required for ingest_url")
            logger.info("Ingest URL job_id=%s agent_id=%s url=%s", job_id, agent_id_str, url[:80])
            if not get_settings().database_configured:
                set_agent_indexing_status(agent_id_str, "error", error_message="Database required for URL ingest")
                raise ValueError("DATABASE_URL required in worker for URL ingest")
            count = ingest_one_url_sync(uuid.UUID(agent_id_str), url)
            set_agent_indexing_status(agent_id_str, "completed")
            duration_ms = int((time.monotonic() - started) * 1000)
            logger.info(
                "Ingest URL completed job_id=%s agent_id=%s documents_count=%s",
                job_id,
                agent_id_str,
                count,
            )
            log_queue_event(
                job_id,
                agent_id_str,
                "ingest_url",
                "completed",
                duration_ms=duration_ms,
                documents_count=count,
                queue_name=QUEUE_NAME,
            )
    except Exception as e:
        logger.exception("run_job_sync failed job_id=%s job_type=%s: %s", job_id, job_type, e)
        set_agent_indexing_status(agent_id_str, "error", error_message=str(e))
        log_queue_event(job_id, agent_id_str, job_type, "failed", error=str(e), queue_name=QUEUE_NAME)
        raise
