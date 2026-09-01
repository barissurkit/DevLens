from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_required_authenticated_user
from app.db.database import get_session
from app.db.models import ActionPlanTask, User
from app.db.repositories.action_plan import delete_task, get_task, list_tasks, utc_now
from app.schemas.action_plan import ActionPlanResponse, ActionPlanTaskCreate, ActionPlanTaskResponse, ActionPlanTaskUpdate, ActionPlanStatus

router = APIRouter(prefix="/api/v1/workspace/action-plan", tags=["Action Plan"])


def require_workspace_origin(request: Request, origin: str | None, content_type: str | None = None) -> None:
    settings = request.app.state.settings
    if origin != settings.auth_frontend_origin:
        raise HTTPException(status_code=403, detail="Invalid request origin.")
    if content_type != "application/json":
        raise HTTPException(status_code=415, detail="Action Plan mutations require application/json.")


async def require_task(request: Request, response: Response, session: AsyncSession = Depends(get_session)) -> User:
    return await get_required_authenticated_user(request, response, session)


def apply_task_update(task: ActionPlanTask, changes: dict[str, object]) -> None:
    status = changes.get("status")
    if status is not None:
        status_value = str(status)
        if status_value == ActionPlanStatus.DONE and task.status != ActionPlanStatus.DONE:
            task.completed_at = utc_now()
        elif status_value != ActionPlanStatus.DONE:
            task.completed_at = None
        changes["status"] = status_value
    for key, value in changes.items():
        setattr(task, key, value)


@router.get("", response_model=ActionPlanResponse)
async def get_action_plan(user: User = Depends(require_task), session: AsyncSession = Depends(get_session)) -> ActionPlanResponse:
    return ActionPlanResponse(tasks=await list_tasks(session, user.id))


@router.post("", response_model=ActionPlanTaskResponse, status_code=201)
async def create_action_plan_task(
    payload: ActionPlanTaskCreate,
    request: Request,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    user: User = Depends(require_task),
    session: AsyncSession = Depends(get_session),
) -> ActionPlanTask:
    require_workspace_origin(request, origin, content_type)
    task = ActionPlanTask(user_id=user.id, title=payload.title, description=payload.description)
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task


@router.patch("/{task_id}", response_model=ActionPlanTaskResponse)
async def update_action_plan_task(
    task_id: UUID,
    payload: ActionPlanTaskUpdate,
    request: Request,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    user: User = Depends(require_task),
    session: AsyncSession = Depends(get_session),
) -> ActionPlanTask:
    require_workspace_origin(request, origin, content_type)
    task = await get_task(session, user.id, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    changes = payload.model_dump(exclude_unset=True)
    apply_task_update(task, changes)
    await session.commit()
    await session.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_action_plan_task(
    task_id: UUID,
    request: Request,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    user: User = Depends(require_task),
    session: AsyncSession = Depends(get_session),
) -> None:
    require_workspace_origin(request, origin, content_type)
    if not await delete_task(session, user.id, task_id):
        raise HTTPException(status_code=404, detail="Task not found.")
    await session.commit()
