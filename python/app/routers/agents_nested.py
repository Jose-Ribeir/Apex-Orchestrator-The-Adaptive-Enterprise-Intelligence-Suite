"""Nested agent routes: instructions, tools, queries (under /api/agents/{agent_id}/...)."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.db import session_scope
from app.models import Agent, AgentInstruction, AgentTool, ModelQuery, Tool
from app.services.agent_service import get_agent

router = APIRouter(prefix="/agents")


def _ensure_agent_owner(agent_id: UUID, user_id: str) -> Agent:
    agent = get_agent(agent_id, user_id=user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ---- Instructions ----
class InstructionCreateBody(BaseModel):
    content: str
    order: int = 0


class InstructionUpdateBody(BaseModel):
    content: str | None = None
    order: int | None = None


@router.get(
    "/{agent_id}/instructions",
    summary="List agent instructions",
    description="Paginated list of instructions for an agent.",
    operation_id="listAgentInstructions",
    tags=["Agents -> Instructions"],
)
async def list_instructions(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _list():
        with session_scope() as session:
            rows = (
                session.query(AgentInstruction)
                .filter(AgentInstruction.agent_id == agent_id, AgentInstruction.is_deleted == False)
                .order_by(AgentInstruction.order)
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            total = (
                session.query(AgentInstruction)
                .filter(AgentInstruction.agent_id == agent_id, AgentInstruction.is_deleted == False)
                .count()
            )
            return [
                {
                    "id": str(r.id),
                    "agentId": str(r.agent_id),
                    "content": r.content,
                    "order": r.order,
                    "createdAt": r.created_at.isoformat(),
                    "updatedAt": r.updated_at.isoformat(),
                }
                for r in rows
            ], total

    items, total = await asyncio.to_thread(_list)
    return {
        "data": items,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
            "more": page * limit < total,
        },
    }


@router.get(
    "/{agent_id}/instructions/{id}",
    summary="Get instruction by ID",
    description="Return a single instruction for an agent.",
    operation_id="getAgentInstruction",
    tags=["Agents -> Instructions"],
)
async def get_instruction(
    agent_id: UUID,
    id: UUID,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _get():
        with session_scope() as session:
            r = (
                session.query(AgentInstruction)
                .filter(
                    AgentInstruction.id == id,
                    AgentInstruction.agent_id == agent_id,
                    AgentInstruction.is_deleted == False,
                )
                .first()
            )
            return r

    r = await asyncio.to_thread(_get)
    if not r:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return {
        "id": str(r.id),
        "agentId": str(r.agent_id),
        "content": r.content,
        "order": r.order,
        "createdAt": r.created_at.isoformat(),
        "updatedAt": r.updated_at.isoformat(),
    }


@router.post(
    "/{agent_id}/instructions",
    status_code=status.HTTP_201_CREATED,
    summary="Create instruction",
    description="Add a new instruction to an agent.",
    operation_id="createAgentInstruction",
    tags=["Agents -> Instructions"],
)
async def create_instruction(
    agent_id: UUID,
    body: InstructionCreateBody,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])
    content = (body.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    def _create():
        with session_scope() as session:
            inst = AgentInstruction(agent_id=agent_id, content=content, order=body.order)
            session.add(inst)
            session.flush()
            session.refresh(inst)
            return inst

    inst = await asyncio.to_thread(_create)
    return {
        "id": str(inst.id),
        "agentId": str(inst.agent_id),
        "content": inst.content,
        "order": inst.order,
        "createdAt": inst.created_at.isoformat(),
        "updatedAt": inst.updated_at.isoformat(),
    }


@router.patch(
    "/{agent_id}/instructions/{id}",
    summary="Update instruction",
    description="Update content or order of an instruction.",
    operation_id="updateAgentInstruction",
    tags=["Agents -> Instructions"],
)
async def update_instruction(
    agent_id: UUID,
    id: UUID,
    body: InstructionUpdateBody,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _update():
        with session_scope() as session:
            r = (
                session.query(AgentInstruction)
                .filter(
                    AgentInstruction.id == id,
                    AgentInstruction.agent_id == agent_id,
                    AgentInstruction.is_deleted == False,
                )
                .first()
            )
            if not r:
                return None
            if body.content is not None:
                r.content = body.content.strip()
            if body.order is not None:
                r.order = body.order
            session.flush()
            session.refresh(r)
            return r

    r = await asyncio.to_thread(_update)
    if not r:
        raise HTTPException(status_code=404, detail="Instruction not found")
    return {
        "id": str(r.id),
        "agentId": str(r.agent_id),
        "content": r.content,
        "order": r.order,
        "createdAt": r.created_at.isoformat(),
        "updatedAt": r.updated_at.isoformat(),
    }


@router.delete(
    "/{agent_id}/instructions/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete instruction",
    description="Soft-delete an instruction.",
    operation_id="deleteAgentInstruction",
    tags=["Agents -> Instructions"],
)
async def delete_instruction(
    agent_id: UUID,
    id: UUID,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _del():
        with session_scope() as session:
            r = (
                session.query(AgentInstruction)
                .filter(AgentInstruction.id == id, AgentInstruction.agent_id == agent_id)
                .first()
            )
            if not r:
                return False
            r.is_deleted = True
            from datetime import datetime, timezone

            r.deleted_at = datetime.now(timezone.utc)
            return True

    ok = await asyncio.to_thread(_del)
    if not ok:
        raise HTTPException(status_code=404, detail="Instruction not found")


# ---- Agent tools (link agent to tool by name) ----
@router.get(
    "/{agent_id}/tools",
    summary="List agent tools",
    description="Paginated list of tools linked to an agent.",
    operation_id="listAgentTools",
    tags=["Agents -> Tools"],
)
async def list_agent_tools(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _list():
        with session_scope() as session:
            base = (
                session.query(AgentTool)
                .filter(AgentTool.agent_id == agent_id)
                .join(Tool)
                .filter(Tool.is_deleted == False)
            )
            total = base.count()
            rows = base.offset((page - 1) * limit).limit(limit).all()
            items = [
                {
                    "id": str(at.tool_id),
                    "name": at.tool.name,
                    "createdAt": at.created_at.isoformat(),
                    "updatedAt": at.tool.updated_at.isoformat() if at.tool.updated_at else at.created_at.isoformat(),
                }
                for at in rows
            ]
            return items, total

    items, total = await asyncio.to_thread(_list)
    pages = (total + limit - 1) // limit if total else 0
    return {
        "data": items,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": pages,
            "more": page < pages,
        },
    }


class AddToolBody(BaseModel):
    name: str


@router.post(
    "/{agent_id}/tools",
    status_code=status.HTTP_201_CREATED,
    summary="Add tool to agent",
    description="Link a tool to an agent by name (creates tool if missing).",
    operation_id="addAgentTool",
    tags=["Agents -> Tools"],
)
async def add_agent_tool(
    agent_id: UUID,
    body: AddToolBody,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])
    name = (body.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    def _add():
        with session_scope() as session:
            from app.services.agent_service import _get_or_create_tool_by_name

            tool = _get_or_create_tool_by_name(session, name)
            existing = (
                session.query(AgentTool).filter(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool.id).first()
            )
            if existing:
                return {
                    "id": str(tool.id),
                    "name": tool.name,
                    "createdAt": tool.created_at.isoformat(),
                    "updatedAt": tool.updated_at.isoformat(),
                }
            at = AgentTool(agent_id=agent_id, tool_id=tool.id)
            session.add(at)
            return {
                "id": str(tool.id),
                "name": tool.name,
                "createdAt": tool.created_at.isoformat(),
                "updatedAt": tool.updated_at.isoformat(),
            }

    return await asyncio.to_thread(_add)


@router.delete(
    "/{agent_id}/tools/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove tool from agent",
    description="Unlink a tool from an agent.",
    operation_id="removeAgentTool",
    tags=["Agents -> Tools"],
)
async def remove_agent_tool(
    agent_id: UUID,
    tool_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _del():
        with session_scope() as session:
            at = session.query(AgentTool).filter(AgentTool.agent_id == agent_id, AgentTool.tool_id == tool_id).first()
            if not at:
                return False
            session.delete(at)
            return True

    ok = await asyncio.to_thread(_del)
    if not ok:
        raise HTTPException(status_code=404, detail="Tool not linked to agent")


# ---- Model queries ----
class ModelQueryCreateBody(BaseModel):
    user_query: str
    model_response: str | None = None
    method_used: str = "EFFICIENCY"


class ModelQueryUpdateBody(BaseModel):
    user_query: str | None = None
    model_response: str | None = None
    method_used: str | None = None


@router.get(
    "/{agent_id}/queries",
    summary="List agent queries",
    description="Paginated list of model queries for an agent.",
    operation_id="listAgentQueries",
    tags=["Agents -> Queries"],
)
async def list_model_queries(
    agent_id: UUID,
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _list():
        with session_scope() as session:
            rows = (
                session.query(ModelQuery)
                .filter(ModelQuery.agent_id == agent_id, ModelQuery.is_deleted == False)
                .order_by(ModelQuery.created_at.desc())
                .offset((page - 1) * limit)
                .limit(limit)
                .all()
            )
            total = (
                session.query(ModelQuery)
                .filter(ModelQuery.agent_id == agent_id, ModelQuery.is_deleted == False)
                .count()
            )
            return [
                {
                    "id": str(r.id),
                    "agentId": str(r.agent_id),
                    "userQuery": r.user_query,
                    "modelResponse": r.model_response,
                    "methodUsed": r.method_used,
                    "createdAt": r.created_at.isoformat(),
                    "updatedAt": r.updated_at.isoformat(),
                }
                for r in rows
            ], total

    items, total = await asyncio.to_thread(_list)
    return {
        "data": items,
        "meta": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit if total else 0,
            "more": page * limit < total,
        },
    }


@router.get(
    "/{agent_id}/queries/{id}",
    summary="Get query by ID",
    description="Return a single model query for an agent.",
    operation_id="getAgentQuery",
    tags=["Agents -> Queries"],
)
async def get_model_query(
    agent_id: UUID,
    id: UUID,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _get():
        with session_scope() as session:
            return (
                session.query(ModelQuery)
                .filter(ModelQuery.id == id, ModelQuery.agent_id == agent_id, ModelQuery.is_deleted == False)
                .first()
            )

    r = await asyncio.to_thread(_get)
    if not r:
        raise HTTPException(status_code=404, detail="Model query not found")
    return {
        "id": str(r.id),
        "agentId": str(r.agent_id),
        "userQuery": r.user_query,
        "modelResponse": r.model_response,
        "methodUsed": r.method_used,
        "createdAt": r.created_at.isoformat(),
        "updatedAt": r.updated_at.isoformat(),
    }


@router.post(
    "/{agent_id}/queries",
    status_code=status.HTTP_201_CREATED,
    summary="Create model query",
    description="Record a user query and optional model response for an agent.",
    operation_id="createAgentQuery",
    tags=["Agents -> Queries"],
)
async def create_model_query(
    agent_id: UUID,
    body: ModelQueryCreateBody,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])
    if not (body.user_query or "").strip():
        raise HTTPException(status_code=400, detail="user_query is required")

    def _create():
        with session_scope() as session:
            q = ModelQuery(
                agent_id=agent_id,
                user_query=body.user_query.strip(),
                model_response=body.model_response,
                method_used=(body.method_used or "EFFICIENCY").upper(),
            )
            session.add(q)
            session.flush()
            session.refresh(q)
            return q

    q = await asyncio.to_thread(_create)
    return {
        "id": str(q.id),
        "agentId": str(q.agent_id),
        "userQuery": q.user_query,
        "modelResponse": q.model_response,
        "methodUsed": q.method_used,
        "createdAt": q.created_at.isoformat(),
        "updatedAt": q.updated_at.isoformat(),
    }


@router.patch(
    "/{agent_id}/queries/{id}",
    summary="Update model query",
    description="Update user query, model response, or method used.",
    operation_id="updateAgentQuery",
    tags=["Agents -> Queries"],
)
async def update_model_query(
    agent_id: UUID,
    id: UUID,
    body: ModelQueryUpdateBody,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _update():
        with session_scope() as session:
            r = (
                session.query(ModelQuery)
                .filter(ModelQuery.id == id, ModelQuery.agent_id == agent_id, ModelQuery.is_deleted == False)
                .first()
            )
            if not r:
                return None
            if body.user_query is not None:
                r.user_query = body.user_query.strip()
            if body.model_response is not None:
                r.model_response = body.model_response
            if body.method_used is not None:
                r.method_used = body.method_used.upper()
            session.flush()
            session.refresh(r)
            return r

    r = await asyncio.to_thread(_update)
    if not r:
        raise HTTPException(status_code=404, detail="Model query not found")
    return {
        "id": str(r.id),
        "agentId": str(r.agent_id),
        "userQuery": r.user_query,
        "modelResponse": r.model_response,
        "methodUsed": r.method_used,
        "createdAt": r.created_at.isoformat(),
        "updatedAt": r.updated_at.isoformat(),
    }


@router.delete(
    "/{agent_id}/queries/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete model query",
    description="Soft-delete a model query.",
    operation_id="deleteAgentQuery",
    tags=["Agents -> Queries"],
)
async def delete_model_query(
    agent_id: UUID,
    id: UUID,
    current_user: dict = Depends(get_current_user),
):
    _ensure_agent_owner(agent_id, current_user["id"])

    def _del():
        with session_scope() as session:
            r = session.query(ModelQuery).filter(ModelQuery.id == id, ModelQuery.agent_id == agent_id).first()
            if not r:
                return False
            r.is_deleted = True
            from datetime import datetime, timezone

            r.deleted_at = datetime.now(timezone.utc)
            return True

    ok = await asyncio.to_thread(_del)
    if not ok:
        raise HTTPException(status_code=404, detail="Model query not found")
