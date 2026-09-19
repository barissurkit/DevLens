import asyncio
import os
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.ext.asyncio import create_async_engine
from fastapi import HTTPException
from starlette.requests import Request

from app.api.action_plan import (
    create_action_plan_task,
    delete_action_plan_task,
    get_action_plan,
    update_action_plan_task,
)
from app.config import Settings
from app.db.database import create_session_factory
from app.db.models import ActionPlanTask, User
from app.db.repositories.action_plan import (
    ACTION_PLAN_MAX_TASKS,
    ActionPlanLimitReachedError,
    create_task,
)
from app.schemas.action_plan import ActionPlanTaskCreate, ActionPlanTaskUpdate

TEST_DATABASE_URL = os.getenv("DEVLENS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


def test_action_plan_cap_is_safe_under_concurrent_creates() -> None:
    if not TEST_DATABASE_URL:
        pytest.skip("DEVLENS_TEST_DATABASE_URL is required for real PostgreSQL tests")

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        user_id = uuid4()
        try:
            async with sessions() as session:
                async with session.begin():
                    session.add(User(id=user_id, github_user_id=uuid4().int % 2**63, github_login=f"h07-{str(user_id)[:8]}"))
                    await session.flush()
                    session.add_all([
                        ActionPlanTask(user_id=user_id, title=f"Task {index}", status=("done" if index % 3 == 0 else "todo"))
                        for index in range(99)
                    ])

            first_ready = asyncio.Event()
            second_ready = asyncio.Event()
            start_second = asyncio.Event()
            second_lock_attempted = asyncio.Event()
            release_first = asyncio.Event()
            second_pid: int | None = None

            loop = asyncio.get_running_loop()

            def observe_second_lock_attempt(connection, cursor, statement, parameters, context, executemany) -> None:
                if connection.info.get("h07_role") == "second" and "FOR UPDATE" in statement:
                    loop.call_soon_threadsafe(second_lock_attempted.set)

            event.listen(engine.sync_engine, "before_cursor_execute", observe_second_lock_attempt)

            async def first_create() -> None:
                async with sessions() as session:
                    async with session.begin():
                        owner = await session.execute(
                            select(User.id).where(User.id == user_id).with_for_update()
                        )
                        assert owner.scalar_one() == user_id
                        count = await session.scalar(
                            select(func.count(ActionPlanTask.id)).where(ActionPlanTask.user_id == user_id)
                        )
                        assert count == 99
                        first_ready.set()
                        await release_first.wait()
                        await create_task(session, user_id, "Task 100", None)

            async def second_create() -> None:
                await first_ready.wait()
                nonlocal second_pid
                async with sessions() as session:
                    async with session.begin():
                        connection = await session.connection()
                        connection.sync_connection.info["h07_role"] = "second"
                        second_pid = await session.scalar(select(func.pg_backend_pid()))
                        second_ready.set()
                        await start_second.wait()
                        with pytest.raises(ActionPlanLimitReachedError):
                            await create_task(session, user_id, "Task 101", None)

            first = asyncio.create_task(first_create())
            await first_ready.wait()
            second = asyncio.create_task(second_create())
            await second_ready.wait()
            start_second.set()
            await asyncio.wait_for(second_lock_attempted.wait(), timeout=5)
            assert second_pid is not None

            async with sessions() as observer_session:
                async def second_is_waiting_for_lock() -> bool:
                    result = await observer_session.execute(
                        text("""
                            SELECT wait_event_type
                            FROM pg_stat_activity
                            WHERE pid = :pid
                        """),
                        {"pid": second_pid},
                    )
                    return result.scalar_one_or_none() == "Lock"

                async def wait_for_second_lock() -> None:
                    while not await second_is_waiting_for_lock():
                        await asyncio.sleep(0.01)

                await asyncio.wait_for(wait_for_second_lock(), timeout=5)
            release_first.set()
            await first
            await second

            async with sessions() as session:
                count = await session.scalar(
                    select(func.count(ActionPlanTask.id)).where(ActionPlanTask.user_id == user_id)
                )
                assert count == ACTION_PLAN_MAX_TASKS
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", observe_second_lock_attempt)
            async with sessions() as session:
                async with session.begin():
                    await session.execute(delete(ActionPlanTask).where(ActionPlanTask.user_id == user_id))
                    await session.execute(delete(User).where(User.id == user_id))
            await engine.dispose()

    asyncio.run(scenario())


def test_action_plan_api_boundaries_and_existing_data_compatibility() -> None:
    if not TEST_DATABASE_URL:
        pytest.skip("DEVLENS_TEST_DATABASE_URL is required for real PostgreSQL tests")

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        user_ids: list[UUID] = []
        settings = Settings(
            _env_file=None,
            frontend_origin="https://devlens.example",
            cors_allowed_origins="https://devlens.example",
        )
        request = Request({"type": "http", "method": "POST", "path": "/"})
        request.scope["app"] = type(
            "App", (), {"state": type("State", (), {"settings": settings})()}
        )()

        async def seed(count: int, *, all_done: bool = False) -> UUID:
            user_id = uuid4()
            user_ids.append(user_id)
            async with sessions() as session:
                async with session.begin():
                    session.add(
                        User(
                            id=user_id,
                            github_user_id=uuid4().int % 2**63,
                            github_login=f"h07-{str(user_id)[:8]}",
                        )
                    )
                    await session.flush()
                    session.add_all([
                        ActionPlanTask(
                            user_id=user_id,
                            title=f"Task {index}",
                            status="done" if all_done else "todo",
                        )
                        for index in range(count)
                    ])
            return user_id

        async def create(user_id: UUID, title: str) -> ActionPlanTask:
            async with sessions() as session:
                return await create_action_plan_task(
                    ActionPlanTaskCreate(title=title),
                    request,
                    "https://devlens.example",
                    "application/json",
                    User(id=user_id, github_user_id=0, github_login="unused"),
                    session,
                )

        try:
            user_99 = await seed(99)
            created = await create(user_99, "Task 100")
            assert created.title == "Task 100"

            user_100_done = await seed(100, all_done=True)
            async with sessions() as session:
                with pytest.raises(HTTPException) as limit_error:
                    await create_action_plan_task(
                        ActionPlanTaskCreate(title="Rejected"),
                        request,
                        "https://devlens.example",
                        "application/json",
                        User(id=user_100_done, github_user_id=0, github_login="unused"),
                        session,
                    )
                assert limit_error.value.status_code == 409
                assert limit_error.value.detail == {
                    "code": "action_plan_limit_reached",
                    "message": "Action Plan görev sınırına ulaşıldı. Yeni görev eklemek için mevcut bir görevi silin.",
                }

            user_101 = await seed(101)
            async with sessions() as session:
                with pytest.raises(HTTPException) as above_cap_error:
                    await create_action_plan_task(
                        ActionPlanTaskCreate(title="Rejected"),
                        request,
                        "https://devlens.example",
                        "application/json",
                        User(id=user_101, github_user_id=0, github_login="unused"),
                        session,
                    )
                assert above_cap_error.value.status_code == 409

            user_delete = await seed(100)
            async with sessions() as session:
                task_result = await session.scalar(
                    select(ActionPlanTask.id).where(ActionPlanTask.user_id == user_delete)
                )
                assert task_result is not None
                await delete_action_plan_task(
                    task_result,
                    request,
                    "https://devlens.example",
                    "application/json",
                    User(id=user_delete, github_user_id=0, github_login="unused"),
                    session,
                )
            recovered = await create(user_delete, "Capacity recovered")
            assert recovered.title == "Capacity recovered"

            user_compat = await seed(101)
            async with sessions() as session:
                response = await get_action_plan(User(id=user_compat, github_user_id=0, github_login="unused"), session)
                assert len(response.tasks) == 101
                task_id = response.tasks[0].id
                updated = await update_action_plan_task(
                    task_id,
                    ActionPlanTaskUpdate(title="Updated above cap"),
                    request,
                    "https://devlens.example",
                    "application/json",
                    User(id=user_compat, github_user_id=0, github_login="unused"),
                    session,
                )
                assert updated.title == "Updated above cap"
                await delete_action_plan_task(
                    task_id,
                    request,
                    "https://devlens.example",
                    "application/json",
                    User(id=user_compat, github_user_id=0, github_login="unused"),
                    session,
                )

            user_independent = await seed(0)
            async with sessions() as session:
                with pytest.raises(HTTPException):
                    await create_action_plan_task(
                        ActionPlanTaskCreate(title="Rejected"),
                        request,
                        "https://devlens.example",
                        "application/json",
                        User(id=user_100_done, github_user_id=0, github_login="unused"),
                        session,
                    )
            independent_created = await create(user_independent, "Independent")
            assert independent_created.title == "Independent"
        finally:
            async with sessions() as session:
                async with session.begin():
                    await session.execute(delete(ActionPlanTask).where(ActionPlanTask.user_id.in_(user_ids)))
                    await session.execute(delete(User).where(User.id.in_(user_ids)))
            await engine.dispose()

    asyncio.run(scenario())
