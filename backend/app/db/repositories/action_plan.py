from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ActionPlanTask


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def list_tasks(session: AsyncSession, user_id: UUID) -> list[ActionPlanTask]:
    result = await session.execute(
        select(ActionPlanTask).where(ActionPlanTask.user_id == user_id).order_by(ActionPlanTask.updated_at.desc())
    )
    return list(result.scalars())


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
