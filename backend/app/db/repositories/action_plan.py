from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActionPlanTask, User

ACTION_PLAN_MAX_TASKS = 100


class ActionPlanLimitReachedError(Exception):
    """Raised when a user has reached the persisted Action Plan task cap."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def list_tasks(session: AsyncSession, user_id: UUID) -> list[ActionPlanTask]:
    result = await session.execute(
        select(ActionPlanTask)
        .where(ActionPlanTask.user_id == user_id)
        .order_by(ActionPlanTask.updated_at.desc(), ActionPlanTask.id.desc())
    )
    return list(result.scalars())


async def create_task(
    session: AsyncSession, user_id: UUID, title: str, description: str | None
) -> ActionPlanTask:
    owner = await session.execute(
        select(User.id).where(User.id == user_id).with_for_update()
    )
    if owner.scalar_one_or_none() is None:
        raise LookupError("Authenticated Action Plan owner was not found.")

    count_result = await session.execute(
        select(func.count(ActionPlanTask.id)).where(ActionPlanTask.user_id == user_id)
    )
    if count_result.scalar_one() >= ACTION_PLAN_MAX_TASKS:
        raise ActionPlanLimitReachedError

    task = ActionPlanTask(user_id=user_id, title=title, description=description)
    session.add(task)
    await session.flush()
    return task


async def get_task(session: AsyncSession, user_id: UUID, task_id: UUID) -> ActionPlanTask | None:
    result = await session.execute(
        select(ActionPlanTask).where(ActionPlanTask.id == task_id, ActionPlanTask.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def delete_task(session: AsyncSession, user_id: UUID, task_id: UUID) -> bool:
    result = await session.execute(
        delete(ActionPlanTask).where(ActionPlanTask.id == task_id, ActionPlanTask.user_id == user_id)
    )
    return result.rowcount == 1
