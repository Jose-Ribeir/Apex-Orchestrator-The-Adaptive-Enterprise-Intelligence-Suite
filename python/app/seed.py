"""Seed default data (e.g. global tools). Idempotent: only inserts missing items."""

import logging

from app.db import session_scope
from app.models import Tool

logger = logging.getLogger("app.seed")

# Default tools available in the catalog
DEFAULT_TOOL_NAMES = [
    "Chain-of-Thought (CoT)",
    "RAG",
    "Straight Model",
    "Web Search",
]


def seed_tools() -> None:
    """Ensure default tools exist. Skips any that already exist (by name)."""
    try:
        with session_scope() as session:
            existing = {r.name for r in session.query(Tool.name).filter(not Tool.is_deleted).all()}
            to_add = [n for n in DEFAULT_TOOL_NAMES if n not in existing]
            for name in to_add:
                session.add(Tool(name=name))
                logger.info("Seeded tool: %s", name)
            if not to_add:
                logger.debug("Default tools already present")
    except Exception as e:
        logger.warning("Seed tools skipped (e.g. DB not ready): %s", e)
