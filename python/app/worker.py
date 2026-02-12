"""BullMQ worker for agent-indexing and agent-prompt-generation queues. Run with: python -m app.worker

With WORKER_RELOAD=1 (or --reload), restarts the worker when Python files under app/ change.
"""

# Bootstrap HuggingFace cache before any imports that might pull in sentence-transformers.
# Avoids G:\ and other missing-drive errors on Windows when embedding model loads.
import os
from pathlib import Path

def _hf_cache_valid(v: str) -> bool:
    if not v or not v.strip():
        return False
    try:
        return Path(v).exists()
    except OSError:
        return False

_wd = Path(__file__).resolve().parent.parent
_hf_cache = _wd / ".cache" / "huggingface"
try:
    _hf_cache.mkdir(parents=True, exist_ok=True)
    for _var in ("HF_HOME", "HUGGINGFACE_HUB_CACHE", "TRANSFORMERS_CACHE"):
        if not _hf_cache_valid(os.environ.get(_var, "")):
            os.environ[_var] = str(_hf_cache)
except OSError:
    pass

import asyncio
import logging
import os
import signal
import sys
import time

from app.config import get_settings
from app.queue_logging import log_queue_event, log_worker_started
from app.services.indexing_queue import QUEUE_NAME as INDEXING_QUEUE
from app.services.indexing_queue import run_job_sync
from app.services.prompt_queue import QUEUE_NAME as PROMPT_QUEUE
from app.services.prompt_queue import run_prompt_job_sync

logger = logging.getLogger("app.worker")

INDEXING_QUEUE_NAME = INDEXING_QUEUE
PROMPT_QUEUE_NAME = PROMPT_QUEUE


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
    logging.getLogger("app.worker").setLevel(logging.INFO)
    logging.getLogger("app.queue").setLevel(logging.INFO)


async def process_indexing(job, job_token):
    """Process one indexing job. job.data has agent_id, job_type, and payload."""
    data = job.data or {}
    job_id = str(getattr(job, "id", "") or "")
    agent_id = data.get("agent_id") or ""
    job_type = data.get("job_type") or ""
    attempt = getattr(job, "attemptsMade", 0) + 1
    started_at = time.monotonic()

    if attempt > 1:
        log_queue_event(job_id, agent_id, job_type, "retrying", attempt=attempt, queue_name=INDEXING_QUEUE_NAME)
    logger.info(
        "Task received: job_id=%s agent_id=%s job_type=%s attempt=%s",
        job_id,
        agent_id,
        job_type,
        attempt,
    )
    log_queue_event(job_id, agent_id, job_type, "received", attempt=attempt, queue_name=INDEXING_QUEUE_NAME)
    log_queue_event(job_id, agent_id, job_type, "processing", attempt=attempt, queue_name=INDEXING_QUEUE_NAME)

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
            queue_name=INDEXING_QUEUE_NAME,
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
            queue_name=INDEXING_QUEUE_NAME,
        )
        raise


async def process_prompt(job, job_token):
    """Process one prompt-generation job. job.data has agent_id."""
    data = job.data or {}
    job_id = str(getattr(job, "id", "") or "")
    agent_id = data.get("agent_id") or ""
    attempt = getattr(job, "attemptsMade", 0) + 1
    job_type = "generate_prompt"
    started_at = time.monotonic()

    if attempt > 1:
        log_queue_event(job_id, agent_id, job_type, "retrying", attempt=attempt, queue_name=PROMPT_QUEUE_NAME)
    log_queue_event(job_id, agent_id, job_type, "received", attempt=attempt, queue_name=PROMPT_QUEUE_NAME)
    log_queue_event(job_id, agent_id, job_type, "processing", attempt=attempt, queue_name=PROMPT_QUEUE_NAME)

    try:
        payload = {**data, "_job_id": job_id}
        await asyncio.to_thread(run_prompt_job_sync, payload)
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
            queue_name=PROMPT_QUEUE_NAME,
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
            queue_name=PROMPT_QUEUE_NAME,
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

    connection = {"connection": settings.redis_url.strip(), "decode_responses": True}

    logger.info("Starting worker for queues %s and %s", INDEXING_QUEUE_NAME, PROMPT_QUEUE_NAME)
    worker_indexing = Worker(INDEXING_QUEUE_NAME, process_indexing, connection)
    worker_prompt = Worker(PROMPT_QUEUE_NAME, process_prompt, connection)
    log_worker_started(INDEXING_QUEUE_NAME, worker_type="indexing")
    log_worker_started(PROMPT_QUEUE_NAME, worker_type="prompt")

    await shutdown.wait()
    logger.info("Closing workers")
    await worker_indexing.close()
    await worker_prompt.close()


def _run_worker() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    _configure_logging()
    reload = os.environ.get("WORKER_RELOAD", "").strip().lower() in ("1", "true", "yes")
    if "--reload" in sys.argv:
        reload = True
        sys.argv = [a for a in sys.argv if a != "--reload"]

    if reload:
        try:
            from watchfiles import run_process
        except ImportError:
            logger.error("WORKER_RELOAD requires watchfiles. pip install watchfiles")
            raise SystemExit(1)
        app_root = os.path.dirname(os.path.abspath(__file__))
        logger.info("Worker starting with reload (watching %s)", app_root)
        run_process(app_root, target=_run_worker)
    else:
        logger.info("Worker process starting (queues: %s, %s)", INDEXING_QUEUE_NAME, PROMPT_QUEUE_NAME)
        asyncio.run(main())
