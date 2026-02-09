"""Prompt generation queue: enqueue generate-prompt jobs (BullMQ) and run them in worker."""

import time
import uuid

from app.config import get_settings
from app.queue_logging import log_queue_event
from app.schemas.requests import AgentConfig
from app.services.agent_service import get_agent, set_agent_enrich_status, update_agent

QUEUE_NAME = "agent-prompt-generation"

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


async def enqueue_generate_prompt(agent_id: uuid.UUID) -> str | None:
    """Enqueue a generate-prompt job for a new agent. Returns job id or None if queue unavailable."""
    q = _get_queue()
    if q is None:
        return None
    agent_id_str = str(agent_id)
    # Retry failed jobs: 10 attempts with exponential backoff (1s, 2s, 4s, ...) so transient
    # failures (e.g. LLM rate limits, network) are retried; permanent failures eventually stop.
    job_opts = {
        "attempts": 10,
        "backoff": {"type": "exponential", "delay": 1000},
    }
    job = await q.add("generate_prompt", {"agent_id": agent_id_str}, job_opts)
    job_id = str(job.id) if job and getattr(job, "id", None) is not None else ""
    if job_id:
        log_queue_event(job_id, agent_id_str, "generate_prompt", "enqueued", queue_name=QUEUE_NAME)
    return job_id


def run_prompt_job_sync(data: dict) -> None:
    """
    Run one prompt-generation job. Called from worker.
    Loads agent, runs optimize_agent_prompt, updates agent.prompt in DB, sets metadata.status.enrich.
    Raises on failure so worker can log and retry.
    """
    agent_id_str = data.get("agent_id") or ""
    job_id = data.get("_job_id", "")
    started = time.monotonic()

    if not agent_id_str:
        raise ValueError("agent_id required")

    from app.services.llm import optimize_agent_prompt

    agent = get_agent(agent_id_str, with_relations=True)
    if not agent:
        log_queue_event(
            job_id,
            agent_id_str,
            "generate_prompt",
            "failed",
            error="Agent not found",
            queue_name=QUEUE_NAME,
        )
        raise ValueError("Agent not found")

    instructions = [i.content for i in sorted(agent.instructions, key=lambda x: x.order)]
    tools = [at.tool.name for at in agent.agent_tools]
    config = AgentConfig(
        agent_id=str(agent.id),
        name=agent.name,
        mode=agent.mode,
        instructions=instructions,
        tools=tools,
    )
    try:
        prompt, _ = optimize_agent_prompt(config)
        update_agent(agent_id_str, prompt=prompt)
        set_agent_enrich_status(agent_id_str, "completed")
    except Exception as e:
        set_agent_enrich_status(agent_id_str, "error", error_message=str(e))
        raise

    duration_ms = int((time.monotonic() - started) * 1000)
    log_queue_event(
        job_id,
        agent_id_str,
        "generate_prompt",
        "completed",
        duration_ms=duration_ms,
        queue_name=QUEUE_NAME,
    )
