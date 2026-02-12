"""Human tasks CRUD."""

from uuid import UUID

from sqlalchemy.orm import joinedload

from app.db import session_scope
from app.models import HumanTask, ModelQuery


def list_tasks(pending_only: bool = False, page: int = 1, limit: int = 20) -> tuple[list, int]:
    offset = (page - 1) * limit
    with session_scope() as session:
        q = session.query(HumanTask).filter(HumanTask.is_deleted.is_(False))
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
            .filter(HumanTask.id == task_id, HumanTask.is_deleted.is_(False))
            .options(joinedload(HumanTask.model_query))
            .first()
        )


def get_task_by_model_query_id(model_query_id: UUID) -> HumanTask | None:
    with session_scope() as session:
        return (
            session.query(HumanTask)
            .filter(HumanTask.model_query_id == model_query_id, HumanTask.is_deleted.is_(False))
            .options(joinedload(HumanTask.model_query))
            .first()
        )


def has_pending_human_task_for_agent(agent_id: UUID) -> bool:
    """Return True if there is at least one PENDING human task for this agent (for natural follow-up context)."""
    with session_scope() as session:
        return (
            session.query(HumanTask.id)
            .join(ModelQuery, HumanTask.model_query_id == ModelQuery.id)
            .filter(
                HumanTask.is_deleted.is_(False),
                HumanTask.status == "PENDING",
                ModelQuery.agent_id == agent_id,
            )
            .limit(1)
            .first()
            is not None
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
    human_resolved_response: str | None = None,
) -> HumanTask | None:
    with session_scope() as session:
        task = session.query(HumanTask).filter(HumanTask.id == task_id, HumanTask.is_deleted.is_(False)).first()
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
        if human_resolved_response is not None:
            task.human_resolved_response = human_resolved_response.strip() or None
        session.flush()
        session.refresh(task)
        return task


def resolve_task(task_id: UUID, human_resolved_response: str | None = None) -> HumanTask | None:
    return update_task(task_id, status="RESOLVED", human_resolved_response=human_resolved_response)


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
