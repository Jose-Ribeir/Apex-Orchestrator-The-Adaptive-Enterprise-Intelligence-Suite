"""BullMQ worker for agent-indexing queue. Run with: python -m app.worker"""

import asyncio
import signal
import time

from app.config import get_settings
from app.queue_logging import log_queue_event, log_worker_started
from app.services.indexing_queue import QUEUE_NAME, run_job_sync


async def process(job, job_token):
    """Process one indexing job. job.data has agent_id, job_type, and payload."""
    data = job.data or {}
    job_id = str(getattr(job, "id", "") or "")
    agent_id = data.get("agent_id") or ""
    job_type = data.get("job_type") or ""
    attempt = getattr(job, "attemptsMade", 0) + 1
    started_at = time.monotonic()

    log_queue_event(job_id, agent_id, job_type, "received", attempt=attempt, queue_name=QUEUE_NAME)
    log_queue_event(job_id, agent_id, job_type, "processing", attempt=attempt, queue_name=QUEUE_NAME)

    try:
        payload = {**data, "_job_id": job_id}
        await asyncio.to_thread(run_job_sync, payload)
        duration_ms = int((time.monotonic() - started_at) * 1000)
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
        raise SystemExit("REDIS_URL is not set. Cannot start worker.")

    shutdown = asyncio.Event()

    def on_signal(*_):
        shutdown.set()

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)

    from bullmq import Worker

    worker = Worker(
        QUEUE_NAME,
        process,
        {"connection": settings.redis_url.strip(), "decode_responses": True},
    )
    log_worker_started(QUEUE_NAME, worker_type="indexing")

    await shutdown.wait()
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
