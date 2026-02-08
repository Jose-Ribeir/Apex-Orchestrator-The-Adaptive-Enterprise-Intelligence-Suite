"""BullMQ worker for agent-prompt-generation queue. Run with: python -m app.prompt_worker"""

import asyncio
import signal

from app.config import get_settings
from app.queue_logging import log_queue_event
from app.services.prompt_queue import QUEUE_NAME, run_prompt_job_sync


async def process(job, job_token):
    """Process one prompt-generation job. job.data has agent_id."""
    data = job.data or {}
    job_id = str(getattr(job, "id", "") or "")
    agent_id = data.get("agent_id") or ""
    attempt = getattr(job, "attemptsMade", 0) + 1

    log_queue_event(job_id, agent_id, "generate_prompt", "started", attempt=attempt, queue_name=QUEUE_NAME)

    try:
        payload = {**data, "_job_id": job_id}
        await asyncio.to_thread(run_prompt_job_sync, payload)
    except Exception as e:
        log_queue_event(
            job_id,
            agent_id,
            "generate_prompt",
            "failed",
            error=str(e),
            attempt=attempt,
            queue_name=QUEUE_NAME,
        )
        raise


async def main():
    settings = get_settings()
    if not settings.queue_configured:
        raise SystemExit("REDIS_URL is not set. Cannot start prompt worker.")

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

    await shutdown.wait()
    await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
