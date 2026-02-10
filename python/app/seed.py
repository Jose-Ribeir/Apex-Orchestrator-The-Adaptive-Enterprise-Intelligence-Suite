"""Seed default data (e.g. global tools, connection types, default user, default agents). Idempotent: only inserts missing items.

To have RAG data ready for the seeded Financial Analyst and Field Service agents, place these
files in app/seed_data/: industry_standards_review.pdf, company_policy_memo.pdf,
q3_financial_report.pdf, parts_catalog.csv. Missing files are skipped with a warning.

When the queue (Redis) is configured, seed enqueues ingest jobs so the worker creates RAG embeddings,
then polls until each agent has the expected document count (or timeout). When the queue is not
configured, ingest runs in-process and embeddings are created in the API process.
"""

import asyncio
import base64
import logging
from pathlib import Path

from app.auth.db import create_user, get_user_by_email
from app.auth.utils import hash_password
from app.db import session_scope
from app.models import Agent, ConnectionType, Tool

logger = logging.getLogger("app.seed")

# Default user(s) created if not present (email, plain password)
DEFAULT_USERS = [
    {"email": "admin@geminimesh.com", "password": "3Fw4G9RfXiJRztNoiCNdwgGg", "name": "Admin"},
]

# Default tools available in the catalog
DEFAULT_TOOL_NAMES = [
    "Chain-of-Thought (CoT)",
    "RAG",
    "Straight Model",
    "Web Search",
    "Python Interpreter",
    "human-in-loop",
]

# Supported connection types (OAuth providers)
DEFAULT_CONNECTION_TYPES = [
    {"name": "Google", "provider_key": "google"},
]

# Seed data directory (app/seed_data/): place PDFs and CSV here for RAG preload
_SEED_DATA_DIR = Path(__file__).resolve().parent / "seed_data"

# Default agents: name, mode, instructions (one string per agent), tools, and RAG filenames to ingest
FINANCIAL_ANALYST_AGENT = {
    "name": "Financial Analyst Agent",
    "mode": "BALANCED",
    "instructions": [
        "You are a specialized Financial Analyst Agent designed to interpret corporate reports and industry standards.\n"
        "Always prioritize using the RAG tool to retrieve exact facts from uploaded PDF documents before answering.\n"
        "When analyzing warranty periods or financial figures, cross-reference the internal Q3 report with the Industry Standards Review.\n"
        "If a user asks for a comparison, explicitly state the values found in the internal documents versus the external benchmarks.\n"
        "Keep your answers professional, fact-based, and directly supported by the retrieved context.",
    ],
    "tools": ["RAG"],
    "rag_files": ["industry_standards_review.pdf", "company_policy_memo.pdf", "q3_financial_report.pdf"],
}

FIELD_SERVICE_ASSISTANT_AGENT = {
    "name": "Field Service Assistant",
    "mode": "BALANCED",
    "instructions": [
        "You are a Field Service Assistant helping technicians identify parts and check inventory.\n"
        "When a user uploads an image, analyze it visually to identify the specific car part and the damage (e.g., cracks, wear).\n"
        "Once the part is identified, use the Python tool to search the 'parts_catalog.csv' file for its 'Part_Name', 'Stock_Level', and 'Price_USD'.\n"
        "CRITICAL SAFETY PROTOCOL: If the visual analysis reveals a dangerous failure (e.g., fuel leak, structural crack in a critical component) "
        "or if the part is completely out of stock, you must STOP and recommend contacting a human supervisor immediately.\n"
        "In these critical cases, output the message: \"⚠️ CRITICAL ISSUE DETECTED: Human Supervisor Review Required.\" and do not proceed with standard repair advice.\n"
        "Otherwise, provide the Part ID and current stock level in your final response.",
    ],
    "tools": ["RAG", "Python Interpreter", "Web Search", "human-in-loop"],
    "rag_files": ["parts_catalog.csv"],
}


def seed_users() -> None:
    """Ensure default users exist. Skips any that already exist (by email)."""
    try:
        for u in DEFAULT_USERS:
            if get_user_by_email(u["email"]) is not None:
                continue
            create_user(
                email=u["email"],
                name=u.get("name") or u["email"].split("@")[0],
                hashed_password=hash_password(u["password"]),
            )
            logger.info("Seeded user: %s", u["email"])
    except Exception as e:
        logger.warning("Seed users skipped (e.g. DB not ready): %s", e)


def seed_connection_types() -> None:
    """Ensure default connection types exist. Skips any that already exist (by provider_key)."""
    try:
        with session_scope() as session:
            existing = {r[0] for r in session.query(ConnectionType.provider_key).all()}
            for item in DEFAULT_CONNECTION_TYPES:
                if item["provider_key"] not in existing:
                    session.add(ConnectionType(name=item["name"], provider_key=item["provider_key"]))
                    logger.info("Seeded connection type: %s", item["provider_key"])
    except Exception as e:
        logger.warning("Seed connection types skipped (e.g. DB not ready): %s", e)


def seed_tools() -> None:
    """Ensure default tools exist. Skips any that already exist (by name)."""
    try:
        with session_scope() as session:
            existing = {r.name for r in session.query(Tool.name).filter(Tool.is_deleted.is_(False)).all()}
            to_add = [n for n in DEFAULT_TOOL_NAMES if n not in existing]
            for name in to_add:
                session.add(Tool(name=name))
                logger.info("Seeded tool: %s", name)
            if not to_add:
                logger.debug("Default tools already present")
    except Exception as e:
        logger.warning("Seed tools skipped (e.g. DB not ready): %s", e)


# Timeout (seconds) to wait for worker to create RAG embeddings after enqueuing seed ingest jobs
_SEED_RAG_WAIT_TIMEOUT = 120
_SEED_RAG_POLL_INTERVAL = 2


async def seed_agents() -> None:
    """Create default agents and ingest RAG files from seed_data/. When queue is configured, enqueues jobs so the worker creates embeddings and polls until done."""
    try:
        from app.config import get_settings
        from app.services.agent_service import create_agent, set_agent_indexing_status
        from app.services.documents_service import ingest_one_file_sync, list_documents
        from app.services.indexing_queue import enqueue_ingest

        user = get_user_by_email("admin@geminimesh.com")
        if user is None:
            logger.warning("Seed agents skipped: default user admin@geminimesh.com not found (run seed_users first)")
            return
        user_id = user["id"]

        # (agent_id, name, expected_doc_count, list of (filename, content))
        agents_to_fill: list[tuple] = []

        for agent_def in (FINANCIAL_ANALYST_AGENT, FIELD_SERVICE_ASSISTANT_AGENT):
            name = agent_def["name"]
            with session_scope() as session:
                existing = (
                    session.query(Agent)
                    .filter(Agent.user_id == user_id, Agent.name == name, Agent.is_deleted.is_(False))
                    .first()
                )
            if existing is not None:
                logger.debug("Seed agent already exists: %s", name)
                agent_id = existing.id
            else:
                agent = create_agent(
                    user_id=user_id,
                    name=name,
                    mode=agent_def["mode"],
                    prompt=None,
                    instructions=agent_def["instructions"],
                    tools=agent_def["tools"],
                )
                agent_id = agent.id
                logger.info("Seeded agent: %s", name)

            _, total_docs = list_documents(agent_id, page=1, limit=1)
            if total_docs > 0:
                logger.debug("Agent %s already has documents, skipping RAG seed", name)
                continue

            if not _SEED_DATA_DIR.is_dir():
                logger.warning("Seed data dir not found: %s (place PDFs/CSV there for RAG preload)", _SEED_DATA_DIR)
                continue

            files_to_ingest: list[tuple[str, bytes]] = []
            for filename in agent_def["rag_files"]:
                path = _SEED_DATA_DIR / filename
                if not path.is_file():
                    logger.warning("Seed RAG file not found: %s", path)
                    continue
                try:
                    content = path.read_bytes()
                    files_to_ingest.append((filename, content))
                except Exception as e:
                    logger.warning("Seed RAG read failed for %s %s: %s", name, filename, e)

            if files_to_ingest:
                agents_to_fill.append((agent_id, name, len(files_to_ingest), files_to_ingest))

        if not agents_to_fill:
            return

        settings = get_settings()
        use_queue = settings.queue_configured

        if use_queue:
            # Enqueue ingest jobs so the worker creates RAG embeddings
            for agent_id, name, expected_count, files_to_ingest in agents_to_fill:
                for filename, content in files_to_ingest:
                    try:
                        content_b64 = base64.b64encode(content).decode("ascii")
                        job_id = await enqueue_ingest(agent_id, filename, content_b64)
                        if job_id:
                            set_agent_indexing_status(agent_id, "pending")
                            logger.info("Seeded RAG enqueued for %s: %s (job_id=%s)", name, filename, job_id)
                        else:
                            logger.warning("Seed RAG enqueue failed for %s %s (queue unavailable)", name, filename)
                    except Exception as e:
                        logger.warning("Seed RAG enqueue failed for %s %s: %s", name, filename, e)

            # Poll until each agent has the expected number of documents (worker has created embeddings)
            elapsed = 0
            done_agent_ids = set()
            while elapsed < _SEED_RAG_WAIT_TIMEOUT:
                await asyncio.sleep(_SEED_RAG_POLL_INTERVAL)
                elapsed += _SEED_RAG_POLL_INTERVAL
                for agent_id, name, expected_count, _ in agents_to_fill:
                    if agent_id in done_agent_ids:
                        continue
                    _, total = list_documents(agent_id, page=1, limit=1)
                    if total >= expected_count:
                        set_agent_indexing_status(agent_id, "completed")
                        done_agent_ids.add(agent_id)
                        logger.info("Seed RAG completed for %s (%s documents)", name, total)
                if len(done_agent_ids) == len(agents_to_fill):
                    logger.info("Seed RAG: all agents have embeddings (worker completed)")
                    return
            logger.warning(
                "Seed RAG: timeout after %ss waiting for worker; ensure worker is running and Redis is configured",
                _SEED_RAG_WAIT_TIMEOUT,
            )
        else:
            # No queue: run ingest in-process (embeddings created in API process)
            for agent_id, name, _expected_count, files_to_ingest in agents_to_fill:
                for filename, content in files_to_ingest:
                    try:
                        count = ingest_one_file_sync(agent_id, filename, content)
                        set_agent_indexing_status(agent_id, "completed")
                        logger.info("Seeded RAG for %s: %s (%s chunks)", name, filename, count)
                    except Exception as e:
                        logger.warning("Seed RAG ingest failed for %s %s: %s", name, filename, e)
                        set_agent_indexing_status(agent_id, "error", error_message=str(e))
    except Exception as e:
        logger.warning("Seed agents skipped (e.g. DB/storage not ready): %s", e)
