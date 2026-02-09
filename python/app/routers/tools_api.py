"""Tools API (under /api/tools)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.schemas.responses import ListToolsResponse, PaginationMeta, ToolItem
from app.services import tools_service

router = APIRouter(prefix="/tools", tags=["Tools"])


class CreateToolBody(BaseModel):
    name: str


class UpdateToolBody(BaseModel):
    name: str


@router.get(
    "",
    summary="List tools",
    description="Paginated list of all tools in the registry.",
    operation_id="listTools",
    response_model=ListToolsResponse,
)
async def list_tools(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    rows, total = tools_service.list_tools(page=page, limit=limit)
    pages = (total + limit - 1) // limit if total else 0
    return ListToolsResponse(
        data=[
            ToolItem(
                id=str(t.id),
                name=t.name,
                createdAt=t.created_at.isoformat(),
                updatedAt=t.updated_at.isoformat(),
            )
            for t in rows
        ],
        meta=PaginationMeta(page=page, limit=limit, total=total, pages=pages, more=page < pages),
    )


@router.get(
    "/{tool_id}",
    summary="Get tool by ID",
    description="Return a single tool by ID.",
    operation_id="getTool",
)
async def get_tool(
    tool_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    tool = tools_service.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "id": str(tool.id),
        "name": tool.name,
        "createdAt": tool.created_at.isoformat(),
        "updatedAt": tool.updated_at.isoformat(),
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create tool",
    description="Create a new tool in the registry by name.",
    operation_id="createTool",
)
async def create_tool(
    body: CreateToolBody,
    current_user: dict = Depends(get_current_user),
):
    try:
        tool = tools_service.create_tool(body.name)
        return {
            "id": str(tool.id),
            "name": tool.name,
            "createdAt": tool.created_at.isoformat(),
            "updatedAt": tool.updated_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{tool_id}",
    summary="Update tool",
    description="Update tool name by ID.",
    operation_id="updateTool",
)
async def update_tool(
    tool_id: UUID,
    body: UpdateToolBody,
    current_user: dict = Depends(get_current_user),
):
    try:
        tool = tools_service.update_tool(tool_id, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return {
        "id": str(tool.id),
        "name": tool.name,
        "createdAt": tool.created_at.isoformat(),
        "updatedAt": tool.updated_at.isoformat(),
    }


@router.delete(
    "/{tool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tool",
    description="Soft delete (default) or hard delete a tool.",
    operation_id="deleteTool",
)
async def delete_tool(
    tool_id: UUID,
    current_user: dict = Depends(get_current_user),
    soft: bool = Query(True, description="Soft delete (default)"),
):
    ok = tools_service.delete_tool(tool_id, soft=soft)
    if not ok:
        raise HTTPException(status_code=404, detail="Tool not found")
