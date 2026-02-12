"""Human tasks API (under /api/human-tasks)."""

import base64
import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.auth.deps import get_current_user
from app.schemas.responses import (
    HumanTaskModelQueryRef,
    HumanTaskResponse,
    ListHumanTasksResponse,
    PaginationMeta,
)
from app.services import connections_service, gmail_service, human_tasks_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/human-tasks", tags=["Human Tasks"])


class ResolveHumanTaskAttachment(BaseModel):
    mime_type: str = Field(..., description="MIME type of the attachment")
    data_base64: str = Field(..., description="Base64-encoded content")


class ResolveHumanTaskBody(BaseModel):
    """Optional body when resolving: human's response and/or attachments to format and send."""

    human_message: str | None = Field(
        None, description="Human's reply text; will be formatted and sent if task has email action"
    )
    attachments: list[ResolveHumanTaskAttachment] | None = Field(
        None, description="Optional attachments (e.g. images/documents)"
    )


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
        humanResolvedResponse=getattr(task, "human_resolved_response", None),
        createdAt=task.created_at.isoformat(),
        updatedAt=task.updated_at.isoformat(),
        modelQuery=(
            HumanTaskModelQueryRef(
                id=str(mq.id),
                userQuery=mq.user_query,
                modelResponse=mq.model_response,
                flowLog=getattr(mq, "flow_log", None),
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


# MIME types we pass to the model as multimodal (images and common docs Gemini can handle)
_MULTIMODAL_MIMES = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp", "image/heic", "application/pdf"}
)


def _format_human_response(
    human_message: str,
    attachments: list[ResolveHumanTaskAttachment] | None = None,
) -> str:
    """Use LLM to turn the human's message and optional attachments into a short professional reply.
    Supports multimodal input (images, PDF). Returns formatted text for email or chat delivery.
    """
    from app.config import get_settings

    settings = get_settings()
    raw_text = (human_message or "").strip()
    if not getattr(settings, "gemini_api_key", None) or not settings.gemini_api_key.strip():
        return raw_text
    attachment_list = attachments or []
    # Build list of dicts for multimodal (mime_type, data_base64) - only supported types
    att_dicts: list[dict[str, str]] = []
    for a in attachment_list:
        mime = (a.mime_type or "").strip().lower()
        if mime in _MULTIMODAL_MIMES and a.data_base64:
            att_dicts.append({"mime_type": a.mime_type, "data_base64": a.data_base64})
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.gemini_api_key.strip())
        prompt = (
            "Given the reviewer's message and any attached images/documents, produce a short, professional reply. "
            "Incorporate relevant information from the attachments. Output only the reply body (no subject, no redundant greetings). "
            "Keep the same intent and key information.\n\n"
            f"Reviewer's message:\n{raw_text or '(none)'}"
        )
        if not att_dicts:
            resp = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
            )
            text = (getattr(resp, "text", None) or "").strip()
            return text or raw_text
        # Multimodal: build Content with text + inline_data parts
        Content = getattr(types, "Content", None)
        Part = getattr(types, "Part", None)
        Blob = getattr(types, "Blob", None)
        if not all((Content, Part, Blob)):
            return raw_text
        parts: list[Any] = [Part(text=prompt)]
        for att in att_dicts:
            mime = att.get("mime_type") or "application/octet-stream"
            b64 = att.get("data_base64") or ""
            try:
                data = base64.b64decode(b64, validate=True)
            except Exception:
                continue
            parts.append(Part(inline_data=Blob(mime_type=mime, data=data)))
        contents = [Content(role="user", parts=parts)]
        resp = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=contents,
        )
        text = (getattr(resp, "text", None) or "").strip()
        return text or raw_text
    except Exception as e:
        logger.warning("Format human response failed: %s", e, exc_info=True)
        return raw_text


@router.post(
    "/{task_id}/resolve",
    response_model=HumanTaskResponse,
    summary="Resolve human task",
    description="Mark a human task as resolved. Optional body: human_message and attachments; if provided, model formats and sends (email) or stores (chat) then resolve.",
    operation_id="resolveHumanTask",
)
async def resolve_task(
    task_id: UUID,
    body: ResolveHumanTaskBody | None = Body(None),
    current_user: dict = Depends(get_current_user),
):
    task = await asyncio.to_thread(human_tasks_service.get_task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Human task not found")
    user_id = current_user["id"]
    get_token = lambda uid: connections_service.get_valid_access_token(uid, "google_gmail")

    formatted_response: str | None = None
    if body and (body.human_message or (body.attachments and len(body.attachments) > 0)):
        formatted_response = _format_human_response(
            (body.human_message or "").strip(),
            body.attachments,
        )

    if task.status == "PENDING" and task.retrieved_data:
        action_data = None
        try:
            action_data = json.loads(task.retrieved_data)
        except (json.JSONDecodeError, TypeError):
            pass

        if isinstance(action_data, dict) and action_data.get("action") in ("send_email", "reply_email"):
            if formatted_response is not None:
                action_data = {**action_data, "body": formatted_response}
                if body and body.attachments:
                    action_data["attachments"] = [
                        {"mime_type": a.mime_type, "data_base64": a.data_base64}
                        for a in body.attachments
                    ]
                await asyncio.to_thread(
                    gmail_service.execute_email_action,
                    user_id,
                    action_data,
                    get_token,
                )
            else:
                await asyncio.to_thread(
                    gmail_service.execute_email_action,
                    user_id,
                    action_data,
                    get_token,
                )
    elif formatted_response is not None:
        # Content-triggered (or other non-email) task: store formatted response for chat delivery
        task = await asyncio.to_thread(
            human_tasks_service.resolve_task,
            task_id,
            human_resolved_response=formatted_response,
        )
        if not task:
            raise HTTPException(status_code=404, detail="Human task not found")
        return _task_to_response(task)

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
