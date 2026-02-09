"""Agent CRUD: DB is source of truth; RAG doc count merged when available."""

import uuid
from typing import overload

from sqlalchemy.orm import joinedload

from app.db import session_scope
from app.models import Agent, AgentDocument, AgentInstruction, AgentTool, Tool
from app.schemas.responses import (
    AgentDetailResponse,
    AgentMetadata,
    AgentMode,
    AgentStatusIndexing,
    AgentToolRef,
)
from app.services.documents_service import _doc_rag_ids
from app.services.rag import get_or_create_retriever


def _rag_doc_count(agent_id: str) -> int:
    try:
        return get_or_create_retriever(agent_id).count_documents()
    except Exception:
        return 0


def _parse_uuid(s: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(s).strip())
    except (ValueError, TypeError):
        return None


def _get_or_create_tool_by_name(session, name_or_id: str) -> Tool:
    name_or_id = (name_or_id or "").strip()
    if not name_or_id:
        raise ValueError("Tool name or id must be non-empty")
    # If value looks like a UUID, resolve by ID first (e.g. frontend may send tool IDs)
    tool_id = _parse_uuid(name_or_id)
    if tool_id is not None:
        tool = session.query(Tool).filter(Tool.id == tool_id, not Tool.is_deleted).first()
        if tool:
            return tool
    # Resolve or create by name
    tool = session.query(Tool).filter(Tool.name == name_or_id, not Tool.is_deleted).first()
    if tool:
        return tool
    tool = Tool(name=name_or_id)
    session.add(tool)
    session.flush()
    return tool


def create_agent(
    *,
    user_id: str,
    name: str,
    mode: str = "EFFICIENCY",
    prompt: str | None = None,
    instructions: list[str] | None = None,
    tools: list[str] | None = None,
) -> Agent:
    """Create agent in DB and initialize RAG. Agent ID is always server-generated. Returns the created Agent."""
    aid = uuid.uuid4()
    instructions = instructions or []
    tools = tools or []

    default_metadata = {"status": {"indexing": "completed", "enrich": "pending"}}
    with session_scope() as session:
        agent = Agent(
            id=aid,
            user_id=user_id.strip(),
            name=name.strip(),
            mode=(mode or "EFFICIENCY").strip().upper() or "EFFICIENCY",
            prompt=prompt.strip() if prompt else None,
            metadata_=default_metadata,
        )
        session.add(agent)
        session.flush()
        for i, content in enumerate(instructions):
            if not (content and str(content).strip()):
                continue
            session.add(
                AgentInstruction(
                    agent_id=agent.id,
                    content=content.strip(),
                    order=i,
                )
            )
        for tool_name in tools:
            tool = _get_or_create_tool_by_name(session, tool_name)
            session.add(AgentTool(agent_id=agent.id, tool_id=tool.id))
        session.refresh(agent)

    get_or_create_retriever(str(agent.id))
    return agent


def set_agent_indexing_status(
    agent_id: uuid.UUID | str,
    status: str,
    error_message: str | None = None,
) -> bool:
    """Set metadata.status.indexing to pending | completed | error.
    Merges into existing metadata. Returns True if updated."""
    if status not in ("pending", "completed", "error"):
        raise ValueError("status must be one of: pending, completed, error")
    aid = uuid.UUID(str(agent_id)) if isinstance(agent_id, str) else agent_id
    with session_scope() as session:
        agent = session.query(Agent).filter(Agent.id == aid, not Agent.is_deleted).first()
        if agent is None:
            return False
        current = agent.metadata_ or {}
        if not isinstance(current, dict):
            current = {}
        status_obj = (current.get("status") or {}) if isinstance(current.get("status"), dict) else {}
        status_obj["indexing"] = status
        if error_message is not None:
            status_obj["indexing_error"] = error_message
        current["status"] = status_obj
        agent.metadata_ = current
        session.flush()
    return True


def set_agent_enrich_status(
    agent_id: uuid.UUID | str,
    status: str,
    error_message: str | None = None,
) -> bool:
    """Set metadata.status.enrich to pending | completed | error.
    Merges into existing metadata. Returns True if updated."""
    if status not in ("pending", "completed", "error"):
        raise ValueError("status must be one of: pending, completed, error")
    aid = uuid.UUID(str(agent_id)) if isinstance(agent_id, str) else agent_id
    with session_scope() as session:
        agent = session.query(Agent).filter(Agent.id == aid, not Agent.is_deleted).first()
        if agent is None:
            return False
        current = agent.metadata_ or {}
        if not isinstance(current, dict):
            current = {}
        status_obj = (current.get("status") or {}) if isinstance(current.get("status"), dict) else {}
        status_obj["enrich"] = status
        if error_message is not None:
            status_obj["enrich_error"] = error_message
        current["status"] = status_obj
        agent.metadata_ = current
        session.flush()
    return True


def list_agents_from_db(
    user_id: str | None = None,
    page: int = 1,
    limit: int = 20,
) -> tuple[list[tuple[Agent, int]], int]:
    """List agents from DB (optionally by user_id), with RAG doc count. Returns ([(Agent, doc_count), ...], total)."""
    offset = (page - 1) * limit
    with session_scope() as session:
        q = (
            session.query(Agent)
            .filter(not Agent.is_deleted)
            .options(
                joinedload(Agent.instructions),
                joinedload(Agent.agent_tools).joinedload(AgentTool.tool),
            )
        )
        if user_id is not None:
            q = q.filter(Agent.user_id == user_id)
        total = q.count()
        agents = q.order_by(Agent.updated_at.desc()).offset(offset).limit(limit).all()
        out = []
        for agent in agents:
            doc_count = _rag_doc_count(str(agent.id))
            out.append((agent, doc_count))
        return out, total


@overload
def get_agent(agent_id: str | uuid.UUID, *, user_id: str | None = None) -> Agent | None: ...
@overload
def get_agent(agent_id: str | uuid.UUID, *, user_id: str | None = None, or_raise: bool) -> Agent: ...


def get_agent(
    agent_id: str | uuid.UUID,
    *,
    user_id: str | None = None,
    or_raise: bool = False,
    with_relations: bool = False,
) -> Agent | None:
    """Get agent by id; optionally filter by user_id. If with_relations, eager-load instructions and tools."""
    aid = uuid.UUID(str(agent_id)) if isinstance(agent_id, str) else agent_id
    with session_scope() as session:
        q = session.query(Agent).filter(Agent.id == aid, not Agent.is_deleted)
        if user_id is not None:
            q = q.filter(Agent.user_id == user_id)
        if with_relations:
            q = q.options(
                joinedload(Agent.instructions),
                joinedload(Agent.agent_tools).joinedload(AgentTool.tool),
            )
        agent = q.first()
        if agent is None and or_raise:
            raise LookupError(f"Agent {agent_id} not found")
        if agent is not None:
            session.refresh(agent)
        return agent


def _metadata_from_agent(agent: Agent) -> AgentMetadata:
    """Build AgentMetadata from attached agent (must be called inside session)."""
    status_obj = (
        (agent.resolved_metadata.get("status") or {}) if isinstance(agent.resolved_metadata.get("status"), dict) else {}
    )
    indexing = status_obj.get("indexing", "completed")
    enrich = status_obj.get("enrich", "pending")
    return AgentMetadata(status=AgentStatusIndexing(indexing=indexing, enrich=enrich))


def get_agent_detail_response(
    agent_id: str | uuid.UUID,
    user_id: str | None = None,
) -> AgentDetailResponse | None:
    """Load agent with relations and build detail response inside session. Returns None if not found."""
    aid = uuid.UUID(str(agent_id)) if isinstance(agent_id, str) else agent_id
    with session_scope() as session:
        q = (
            session.query(Agent)
            .filter(Agent.id == aid, not Agent.is_deleted)
            .options(
                joinedload(Agent.instructions),
                joinedload(Agent.agent_tools).joinedload(AgentTool.tool),
            )
        )
        if user_id is not None:
            q = q.filter(Agent.user_id == user_id)
        agent = q.first()
        if agent is None:
            return None
        doc_count = _rag_doc_count(str(agent.id))
        instructions = [i.content for i in sorted(agent.instructions, key=lambda x: x.order)]
        tools = [AgentToolRef(id=str(at.tool.id), name=at.tool.name) for at in agent.agent_tools]
        return AgentDetailResponse(
            agent_id=str(agent.id),
            user_id=agent.user_id,
            name=agent.name,
            mode=AgentMode(agent.mode),
            prompt=agent.prompt,
            instructions=instructions,
            tools=tools,
            doc_count=doc_count,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            metadata=_metadata_from_agent(agent),
        )


def update_agent(
    agent_id: str | uuid.UUID,
    *,
    user_id: str | None = None,
    name: str | None = None,
    mode: str | None = None,
    prompt: str | None = None,
    instructions: list[str] | None = None,
    tools: list[str] | None = None,
) -> Agent | None:
    """Update agent; returns updated Agent or None if not found."""
    agent = get_agent(agent_id, user_id=user_id)
    if agent is None:
        return None
    aid = agent.id

    with session_scope() as session:
        agent = session.query(Agent).filter(Agent.id == aid, not Agent.is_deleted).first()
        if agent is None:
            return None
        if name is not None:
            agent.name = name.strip()
        if mode is not None:
            agent.mode = mode.strip().upper() or agent.mode
        if prompt is not None:
            agent.prompt = prompt.strip() if prompt else None
        if instructions is not None:
            session.query(AgentInstruction).filter(AgentInstruction.agent_id == aid).delete()
            for i, content in enumerate(instructions):
                if content and str(content).strip():
                    session.add(AgentInstruction(agent_id=aid, content=content.strip(), order=i))
        if tools is not None:
            session.query(AgentTool).filter(AgentTool.agent_id == aid).delete()
            for tool_name in tools:
                tool = _get_or_create_tool_by_name(session, tool_name)
                session.add(AgentTool(agent_id=aid, tool_id=tool.id))
        session.flush()
        agent = (
            session.query(Agent)
            .filter(Agent.id == aid)
            .options(
                joinedload(Agent.instructions),
                joinedload(Agent.agent_tools).joinedload(AgentTool.tool),
            )
            .one()
        )
        session.refresh(agent)
        return agent


def delete_agent(agent_id: str | uuid.UUID, *, user_id: str | None = None, soft: bool = True) -> bool:
    """Soft-delete (or hard-delete) agent. Returns True if found and deleted."""
    agent = get_agent(agent_id, user_id=user_id)
    if agent is None:
        return False
    aid = agent.id

    with session_scope() as session:
        agent = session.query(Agent).filter(Agent.id == aid).first()
        if agent is None:
            return False
        if soft:
            from datetime import datetime, timezone

            agent.is_deleted = True
            agent.deleted_at = datetime.now(timezone.utc)
        else:
            # Clear RAG index for this agent before DB cascade removes document rows
            docs = session.query(AgentDocument).filter(AgentDocument.agent_id == aid).all()
            rag = get_or_create_retriever(str(aid))
            for doc in docs:
                for rag_id in _doc_rag_ids(doc):
                    rag.delete_document(rag_id)
            session.delete(agent)
    return True
