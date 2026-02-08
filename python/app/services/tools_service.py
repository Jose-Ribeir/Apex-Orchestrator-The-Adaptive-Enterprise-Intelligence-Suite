"""Tools CRUD (global tools table)."""

from uuid import UUID

from app.db import session_scope
from app.models import Tool


def list_tools(page: int = 1, limit: int = 20) -> tuple[list[Tool], int]:
    offset = (page - 1) * limit
    with session_scope() as session:
        total = session.query(Tool).filter(Tool.is_deleted == False).count()
        rows = (
            session.query(Tool).filter(Tool.is_deleted == False).order_by(Tool.name).offset(offset).limit(limit).all()
        )
        return list(rows), total


def get_tool(tool_id: UUID) -> Tool | None:
    with session_scope() as session:
        return session.query(Tool).filter(Tool.id == tool_id, Tool.is_deleted == False).first()


def create_tool(name: str) -> Tool:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    with session_scope() as session:
        tool = Tool(name=name)
        session.add(tool)
        session.flush()
        session.refresh(tool)
        return tool


def update_tool(tool_id: UUID, name: str) -> Tool | None:
    name = (name or "").strip()
    if not name:
        raise ValueError("name is required")
    with session_scope() as session:
        tool = session.query(Tool).filter(Tool.id == tool_id, Tool.is_deleted == False).first()
        if not tool:
            return None
        tool.name = name
        session.flush()
        session.refresh(tool)
        return tool


def delete_tool(tool_id: UUID, soft: bool = True) -> bool:
    from datetime import datetime, timezone

    with session_scope() as session:
        tool = session.query(Tool).filter(Tool.id == tool_id).first()
        if not tool:
            return False
        if soft:
            tool.is_deleted = True
            tool.deleted_at = datetime.now(timezone.utc)
        else:
            session.delete(tool)
        return True
