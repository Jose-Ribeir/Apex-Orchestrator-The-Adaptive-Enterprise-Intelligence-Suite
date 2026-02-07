"""Agent CRUD: DB is source of truth; RAG doc count merged when available."""

import uuid
from typing import overload

from sqlalchemy.orm import joinedload

from app.db import session_scope
from app.models import Agent, AgentInstruction, AgentTool, Tool
from app.services.rag import get_or_create_retriever


def _rag_doc_count(agent_id: str) -> int:
    try:
        return get_or_create_retriever(agent_id).count_documents()
    except Exception:
        return 0


def _get_or_create_tool_by_name(session, name: str) -> Tool:
    name = (name or "").strip()
    if not name:
        raise ValueError("Tool name must be non-empty")
    tool = session.query(Tool).filter(Tool.name == name, Tool.is_deleted == False).first()
    if tool:
        return tool
    tool = Tool(name=name)
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
    agent_id: uuid.UUID | str | None = None,
) -> Agent:
    """Create agent in DB and initialize RAG for agent_id. Returns the created Agent."""
    if agent_id is not None:
        aid = uuid.UUID(str(agent_id)) if isinstance(agent_id, str) else agent_id
    else:
        aid = uuid.uuid4()
    instructions = instructions or []
    tools = tools or []

    with session_scope() as session:
        agent = Agent(
            id=aid,
            user_id=user_id.strip(),
            name=name.strip(),
            mode=(mode or "EFFICIENCY").strip().upper() or "EFFICIENCY",
            prompt=prompt.strip() if prompt else None,
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


def list_agents_from_db(user_id: str | None = None) -> list[tuple[Agent, int]]:
    """List agents from DB (optionally by user_id), with RAG doc count. Returns [(Agent, doc_count), ...]."""
    with session_scope() as session:
        q = session.query(Agent).filter(Agent.is_deleted == False)
        if user_id is not None:
            q = q.filter(Agent.user_id == user_id)
        agents = q.order_by(Agent.updated_at.desc()).all()
        out = []
        for agent in agents:
            doc_count = _rag_doc_count(str(agent.id))
            out.append((agent, doc_count))
        return out


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
        q = session.query(Agent).filter(Agent.id == aid, Agent.is_deleted == False)
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
        agent = session.query(Agent).filter(Agent.id == aid, Agent.is_deleted == False).first()
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
            session.delete(agent)
    return True
