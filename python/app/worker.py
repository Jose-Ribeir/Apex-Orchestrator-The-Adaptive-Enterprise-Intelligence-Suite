"""BullMQ worker for agent-indexing queue. Run with: python -m app.worker"""

import asyncio
import logging
import signal
import sys
import time

from app.config import get_settings
from app.queue_logging import log_queue_event, log_worker_started
from app.services.indexing_queue import QUEUE_NAME, run_job_sync

logger = logging.getLogger("app.worker")


def _configure_logging() -> None:
    """Configure logging so output appears in Docker/CI (unbuffered, to stderr)."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    # Ensure app loggers emit
    logging.getLogger("app.worker").setLevel(logging.INFO)
    logging.getLogger("app.queue").setLevel(logging.INFO)


async def process(job, job_token):
    """Process one indexing job. job.data has agent_id, job_type, and payload."""
    data = job.data or {}
    job_id = str(getattr(job, "id", "") or "")
    agent_id = data.get("agent_id") or ""
    job_type = data.get("job_type") or ""
    attempt = getattr(job, "attemptsMade", 0) + 1
    started_at = time.monotonic()

    if attempt > 1:
        log_queue_event(job_id, agent_id, job_type, "retrying", attempt=attempt, queue_name=QUEUE_NAME)
    logger.info(
        "Task received: job_id=%s agent_id=%s job_type=%s attempt=%s",
        job_id,
        agent_id,
        job_type,
        attempt,
    )
    log_queue_event(job_id, agent_id, job_type, "received", attempt=attempt, queue_name=QUEUE_NAME)
    log_queue_event(job_id, agent_id, job_type, "processing", attempt=attempt, queue_name=QUEUE_NAME)

    try:
        payload = {**data, "_job_id": job_id}
        logger.info("Running job job_id=%s job_type=%s", job_id, job_type)
        await asyncio.to_thread(run_job_sync, payload)
        duration_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "Job completed: job_id=%s job_type=%s duration_ms=%s",
            job_id,
            job_type,
            duration_ms,
        )
        log_queue_event(
            job_id,
            agent_id,
            job_type,
            "completed",
            attempt=attempt,
            duration_ms=duration_ms,
            queue_name=QUEUE_NAME,
        )
    except Exception as e:
        logger.exception("Job failed: job_id=%s job_type=%s error=%s", job_id, job_type, e)
        log_queue_event(
            job_id,
            agent_id,
            job_type,
            "failed",
            error=str(e),
            attempt=attempt,
            queue_name=QUEUE_NAME,
        )
        raise


async def main():
    settings = get_settings()
    if not settings.queue_configured:
        logger.error("REDIS_URL is not set. Cannot start worker.")
        raise SystemExit("REDIS_URL is not set. Cannot start worker.")

    shutdown = asyncio.Event()

    def on_signal(*_):
        logger.info("Shutdown signal received")
        shutdown.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    from bullmq import Worker

    logger.info("Starting worker for queue=%s", QUEUE_NAME)
    worker = Worker(
        QUEUE_NAME,
        process,
        {"connection": settings.redis_url.strip(), "decode_responses": True},
    )
    log_worker_started(QUEUE_NAME, worker_type="indexing")

    await shutdown.wait()
    logger.info("Closing worker")
    await worker.close()


if __name__ == "__main__":
    _configure_logging()
    logger.info("Worker process starting (queue=%s)", QUEUE_NAME)
    asyncio.run(main())
