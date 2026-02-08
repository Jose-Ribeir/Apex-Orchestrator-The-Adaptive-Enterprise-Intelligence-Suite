"""Human tasks API (under /api/human-tasks)."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.auth.deps import get_current_user
from app.schemas.responses import (
    HumanTaskModelQueryRef,
    HumanTaskResponse,
    ListHumanTasksResponse,
    PaginationMeta,
)
from app.services import human_tasks_service

router = APIRouter(prefix="/human-tasks", tags=["Human Tasks"])


class CreateHumanTaskBody(BaseModel):
    model_query_id: str
    reason: str
    retrieved_data: str | None = None
    model_message: str
    status: str = "PENDING"


class UpdateHumanTaskBody(BaseModel):
    reason: str | None = None
    retrieved_data: str | None = None
    model_message: str | None = None
    status: str | None = None


def _task_to_response(task) -> HumanTaskResponse:
    mq = task.model_query if hasattr(task, "model_query") and task.model_query else None
    return HumanTaskResponse(
        id=str(task.id),
        modelQueryId=str(task.model_query_id),
        reason=task.reason,
        retrievedData=task.retrieved_data,
        modelMessage=task.model_message,
        status=task.status,
        createdAt=task.created_at.isoformat(),
        updatedAt=task.updated_at.isoformat(),
        modelQuery=(
            HumanTaskModelQueryRef(
                id=str(mq.id),
                userQuery=mq.user_query,
                modelResponse=mq.model_response,
            )
            if mq
            else None
        ),
    )


@router.get(
    "",
    response_model=ListHumanTasksResponse,
    summary="List human tasks",
    description="Paginated list of human-in-the-loop tasks; optional filter by PENDING.",
    operation_id="listHumanTasks",
)
async def list_human_tasks(
    pending: bool = Query(False, description="Filter to PENDING only"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> ListHumanTasksResponse:
    rows, total = await asyncio.to_thread(human_tasks_service.list_tasks, pending, page, limit)
    pages = (total + limit - 1) // limit if total else 0
    return ListHumanTasksResponse(
        data=[_task_to_response(t) for t in rows],
        meta=PaginationMeta(page=page, limit=limit, total=total, pages=pages, more=page < pages),
    )


@router.get(
    "/by-query/{model_query_id}",
    response_model=HumanTaskResponse,
    summary="Get task by model query ID",
    description="Return the human task linked to a model query.",
    operation_id="getHumanTaskByQuery",
)
async def get_by_model_query(
    model_query_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    task = await asyncio.to_thread(human_tasks_service.get_task_by_model_query_id, model_query_id)
    if not task:
        raise HTTPException(status_code=404, detail="Human task not found")
    return _task_to_response(task)


@router.get(
    "/{task_id}",
    response_model=HumanTaskResponse,
    summary="Get human task by ID",
    description="Return a single human task by ID.",
    operation_id="getHumanTask",
)
async def get_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    task = await asyncio.to_thread(human_tasks_service.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Human task not found")
    return _task_to_response(task)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=HumanTaskResponse,
    summary="Create human task",
    description="Create a human-in-the-loop task for a model query.",
    operation_id="createHumanTask",
)
async def create_task(
    body: CreateHumanTaskBody,
    current_user: dict = Depends(get_current_user),
):
    try:
        task = await asyncio.to_thread(
            human_tasks_service.create_task,
            UUID(body.model_query_id),
            body.reason,
            body.model_message,
            body.retrieved_data,
            body.status,
        )
        return _task_to_response(task)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch(
    "/{task_id}",
    response_model=HumanTaskResponse,
    summary="Update human task",
    description="Update reason, retrieved data, model message, or status.",
    operation_id="updateHumanTask",
)
async def update_task(
    task_id: UUID,
    body: UpdateHumanTaskBody,
    current_user: dict = Depends(get_current_user),
):
    task = await asyncio.to_thread(
        human_tasks_service.update_task,
        task_id,
        body.reason,
        body.retrieved_data,
        body.model_message,
        body.status,
    )
    if not task:
        raise HTTPException(status_code=404, detail="Human task not found")
    return _task_to_response(task)


@router.post(
    "/{task_id}/resolve",
    response_model=HumanTaskResponse,
    summary="Resolve human task",
    description="Mark a human task as resolved.",
    operation_id="resolveHumanTask",
)
async def resolve_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    task = await asyncio.to_thread(human_tasks_service.resolve_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Human task not found")
    return _task_to_response(task)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete human task",
    description="Delete a human task by ID.",
    operation_id="deleteHumanTask",
)
async def delete_task(
    task_id: UUID,
    current_user: dict = Depends(get_current_user),
):
    ok = await asyncio.to_thread(human_tasks_service.delete_task, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Human task not found")
