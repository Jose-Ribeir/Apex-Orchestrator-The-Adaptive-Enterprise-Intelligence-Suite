"""Human tasks CRUD."""

from uuid import UUID

from sqlalchemy.orm import joinedload

from app.db import session_scope
from app.models import HumanTask, ModelQuery


def list_tasks(pending_only: bool = False, page: int = 1, limit: int = 20) -> tuple[list, int]:
    offset = (page - 1) * limit
    with session_scope() as session:
        q = session.query(HumanTask).filter(HumanTask.is_deleted == False)
        if pending_only:
            q = q.filter(HumanTask.status == "PENDING")
        total = q.count()
        rows = (
            q.options(joinedload(HumanTask.model_query))
            .order_by(HumanTask.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
        return list(rows), total


def get_task(task_id: UUID) -> HumanTask | None:
    with session_scope() as session:
        return (
            session.query(HumanTask)
            .filter(HumanTask.id == task_id, HumanTask.is_deleted == False)
            .options(joinedload(HumanTask.model_query))
            .first()
        )


def get_task_by_model_query_id(model_query_id: UUID) -> HumanTask | None:
    with session_scope() as session:
        return (
            session.query(HumanTask)
            .filter(HumanTask.model_query_id == model_query_id, HumanTask.is_deleted == False)
            .options(joinedload(HumanTask.model_query))
            .first()
        )


def create_task(
    model_query_id: UUID,
    reason: str,
    model_message: str,
    retrieved_data: str | None = None,
    status: str = "PENDING",
) -> HumanTask:
    reason = (reason or "").strip()
    model_message = (model_message or "").strip()
    if not reason:
        raise ValueError("reason is required")
    if not model_message:
        raise ValueError("modelMessage is required")
    with session_scope() as session:
        mq = session.query(ModelQuery).filter(ModelQuery.id == model_query_id).first()
        if not mq:
            raise LookupError("ModelQuery not found")
        task = HumanTask(
            model_query_id=model_query_id,
            reason=reason,
            model_message=model_message,
            retrieved_data=retrieved_data,
            status=status,
        )
        session.add(task)
        session.flush()
        session.refresh(task)
        return task


def update_task(
    task_id: UUID,
    reason: str | None = None,
    retrieved_data: str | None = None,
    model_message: str | None = None,
    status: str | None = None,
) -> HumanTask | None:
    with session_scope() as session:
        task = session.query(HumanTask).filter(HumanTask.id == task_id, HumanTask.is_deleted == False).first()
        if not task:
            return None
        if reason is not None:
            task.reason = reason.strip()
        if retrieved_data is not None:
            task.retrieved_data = retrieved_data
        if model_message is not None:
            task.model_message = model_message.strip()
        if status is not None:
            task.status = status
        session.flush()
        session.refresh(task)
        return task


def resolve_task(task_id: UUID) -> HumanTask | None:
    return update_task(task_id, status="RESOLVED")


def delete_task(task_id: UUID, soft: bool = True) -> bool:
    from datetime import datetime, timezone

    with session_scope() as session:
        task = session.query(HumanTask).filter(HumanTask.id == task_id).first()
        if not task:
            return False
        if soft:
            task.is_deleted = True
            task.deleted_at = datetime.now(timezone.utc)
        else:
            session.delete(task)
        return True
