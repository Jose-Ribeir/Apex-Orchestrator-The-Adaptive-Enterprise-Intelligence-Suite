"""Seed default data (e.g. global tools, connection types). Idempotent: only inserts missing items."""

import logging

from app.db import session_scope
from app.models import ConnectionType, Tool

logger = logging.getLogger("app.seed")

# Default tools available in the catalog
DEFAULT_TOOL_NAMES = [
    "Chain-of-Thought (CoT)",
    "RAG",
    "Straight Model",
    "Web Search",
]

# Supported connection types (OAuth providers)
DEFAULT_CONNECTION_TYPES = [
    {"name": "Google", "provider_key": "google"},
]


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
