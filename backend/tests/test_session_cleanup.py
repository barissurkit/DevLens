import asyncio
import base64
import hashlib
import os
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import app.api.auth as auth_api
from fastapi import Request, Response
import pytest
from sqlalchemy import delete, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from app.auth.repositories import delete_expired_sessions, utc_now
from app.auth.session_cleanup import (
    SESSION_CLEANUP_BATCH_SIZE,
    SESSION_CLEANUP_INTERVAL_SECONDS,
    SessionCleanupCoordinator,
)
from app.db.database import create_session_factory
from app.db.models import Session, User
from app.config import Settings
from app.schemas.github import GitHubUser


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value


def test_coordinator_throttles_and_retries_after_interval() -> None:
    clock = FakeClock()
    cleanup = AsyncMock(return_value=3)
    coordinator = SessionCleanupCoordinator(clock)

    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) == 3
    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) is None
    clock.value += SESSION_CLEANUP_INTERVAL_SECONDS
    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) == 3
    assert cleanup.await_count == 2


def test_coordinator_claims_interval_once_for_concurrent_calls() -> None:
    clock = FakeClock()
    cleanup = AsyncMock(return_value=1)
    coordinator = SessionCleanupCoordinator(clock)

    async def scenario() -> list[int | None]:
        return await asyncio.gather(
            coordinator.maybe_cleanup(cleanup),
            coordinator.maybe_cleanup(cleanup),
        )

    results = asyncio.run(scenario())

    assert sorted(result is None for result in results) == [False, True]
    assert cleanup.await_count == 1


def test_cleanup_failure_consumes_interval_without_swallowing_programming_errors() -> None:
    clock = FakeClock()
    cleanup = AsyncMock(side_effect=SQLAlchemyError("synthetic database failure"))
    coordinator = SessionCleanupCoordinator(clock)

    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) is None
    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) is None
    assert cleanup.await_count == 1
    clock.value += SESSION_CLEANUP_INTERVAL_SECONDS
    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) is None
    assert cleanup.await_count == 2


def test_cleanup_cancellation_propagates_after_claiming_interval() -> None:
    clock = FakeClock()
    cleanup = AsyncMock(side_effect=asyncio.CancelledError())
    coordinator = SessionCleanupCoordinator(clock)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(coordinator.maybe_cleanup(cleanup))
    assert asyncio.run(coordinator.maybe_cleanup(cleanup)) is None
    assert cleanup.await_count == 1


def test_bounded_cleanup_statement_is_postgresql_safe() -> None:
    result = SimpleNamespace(all=lambda: [object(), object()])
    session = SimpleNamespace(execute=AsyncMock(return_value=result))

    deleted_count = asyncio.run(delete_expired_sessions(session))
    statement = session.execute.await_args.args[0]
    sql = str(statement.compile(dialect=postgresql.dialect()))

    assert deleted_count == 2
    assert "LIMIT" in sql
    assert SESSION_CLEANUP_BATCH_SIZE in statement.compile(
        dialect=postgresql.dialect()
    ).params.values()
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "RETURNING sessions.id" in sql


TEST_DATABASE_URL = os.getenv("DEVLENS_TEST_DATABASE_URL")
postgresql_test = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="DEVLENS_TEST_DATABASE_URL is required for session cleanup integration tests",
)


@postgresql_test
def test_postgresql_cleanup_enforces_boundary_and_batch() -> None:
    assert TEST_DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        user_id = uuid4()
        now = utc_now()
        expired_ids = []
        try:
            async with sessions() as session:
                async with session.begin():
                    session.add(User(id=user_id, github_user_id=uuid4().int % (2**63), github_login=f"cleanup-{user_id.hex[:20]}"))
                    for index in range(SESSION_CLEANUP_BATCH_SIZE + 1):
                        record = Session(
                            user_id=user_id,
                            token_hash=hashlib.sha256(f"expired-{index}-{user_id}".encode()).digest(),
                            expires_at=now - timedelta(seconds=SESSION_CLEANUP_BATCH_SIZE - index),
                        )
                        session.add(record)
                        expired_ids.append(record)
                    session.add(
                        Session(
                            user_id=user_id,
                            token_hash=hashlib.sha256(f"valid-{user_id}".encode()).digest(),
                            expires_at=now + timedelta(days=1),
                        )
                    )

            async with sessions() as session:
                async with session.begin():
                    first_count = await delete_expired_sessions(session)
            async with sessions() as session:
                remaining_after_first = await session.scalars(
                    select(Session).where(Session.user_id == user_id)
                )
                remaining_rows = list(remaining_after_first)
            async with sessions() as session:
                async with session.begin():
                    second_count = await delete_expired_sessions(session)
            assert first_count == SESSION_CLEANUP_BATCH_SIZE
            assert second_count == 1
            assert len(remaining_rows) == 2
            assert any(row.expires_at == now for row in remaining_rows)
            assert any(row.expires_at > now for row in remaining_rows)
        finally:
            async with sessions() as session:
                async with session.begin():
                    user = await session.get(User, user_id)
                    if user is not None:
                        await session.delete(user)
            await engine.dispose()

    asyncio.run(scenario())


@postgresql_test
def test_postgresql_cleanup_skip_locked_uses_disjoint_batches() -> None:
    assert TEST_DATABASE_URL is not None

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        user_id = uuid4()
        now = utc_now()
        session_a = sessions()
        session_b = sessions()
        try:
            async with sessions() as session:
                async with session.begin():
                    session.add(User(id=user_id, github_user_id=uuid4().int % (2**63), github_login=f"lock-{user_id.hex[:20]}"))
                    for index in range(SESSION_CLEANUP_BATCH_SIZE * 2):
                        session.add(
                            Session(
                                user_id=user_id,
                                token_hash=hashlib.sha256(f"locked-{index}-{user_id}".encode()).digest(),
                                expires_at=now - timedelta(seconds=index + 1),
                            )
                        )
                    session.add(
                        Session(
                            user_id=user_id,
                            token_hash=hashlib.sha256(f"valid-{user_id}".encode()).digest(),
                            expires_at=now + timedelta(days=1),
                        )
                    )

            async with session_a.begin():
                locked_query = (
                    select(Session.id)
                    .where(Session.user_id == user_id, Session.expires_at <= now)
                    .order_by(Session.expires_at, Session.id)
                    .limit(SESSION_CLEANUP_BATCH_SIZE)
                    .with_for_update(skip_locked=True)
                )
                locked_ids = list((await session_a.scalars(locked_query)).all())
                assert len(locked_ids) == SESSION_CLEANUP_BATCH_SIZE
                locks_acquired = asyncio.Event()
                cleanup_finished = asyncio.Event()
                cleanup_count: int | None = None

                async def run_second_cleanup() -> None:
                    nonlocal cleanup_count
                    await locks_acquired.wait()
                    async with session_b.begin():
                        cleanup_count = await delete_expired_sessions(session_b)
                    cleanup_finished.set()

                locks_acquired.set()
                cleanup_task = asyncio.create_task(run_second_cleanup())
                await asyncio.wait_for(cleanup_finished.wait(), timeout=5)
                await cleanup_task
                await session_a.execute(delete(Session).where(Session.id.in_(locked_ids)))

            assert cleanup_count == SESSION_CLEANUP_BATCH_SIZE
            async with sessions() as session:
                remaining = list(
                    await session.scalars(select(Session).where(Session.user_id == user_id))
                )
            assert len(remaining) == 1
            assert remaining[0].expires_at > now
        finally:
            await session_a.close()
            await session_b.close()
            async with sessions() as session:
                async with session.begin():
                    user = await session.get(User, user_id)
                    if user is not None:
                        await session.delete(user)
            await engine.dispose()

    asyncio.run(scenario())


def _auth_request(settings: Settings, *, with_session_cookie: bool = True) -> Request:
    headers = (
        [(b"cookie", b"devlens_session=synthetic-session-token")]
        if with_session_cookie
        else []
    )
    application = SimpleNamespace(
        state=SimpleNamespace(
            settings=settings,
            session_cleanup_coordinator=SessionCleanupCoordinator(),
        )
    )
    request = Request(
        {
            "type": "http",
            "headers": headers,
        }
    )
    request.scope["app"] = application
    return request


def _auth_settings() -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        auth_enabled=True,
        database_url="postgresql+asyncpg://synthetic/test",
        frontend_origin="http://localhost:3000",
        cors_allowed_origins="http://localhost:3000",
        github_app_client_id="synthetic-client",
        github_app_client_secret="synthetic-secret",
        github_app_callback_url="http://localhost:8000/api/v1/auth/github/callback",
        auth_state_encryption_key=base64.urlsafe_b64encode(b"k" * 32).decode(),
    )


def test_authenticated_resolution_survives_cleanup_database_failure(monkeypatch) -> None:
    user = User(github_user_id=1, github_login="synthetic-user")
    settings = _auth_settings()
    request = _auth_request(settings)
    monkeypatch.setattr(auth_api, "get_user_by_session_token", AsyncMock(return_value=user))
    monkeypatch.setattr(
        auth_api,
        "get_session_factory",
        lambda _: (_ for _ in ()).throw(SQLAlchemyError("synthetic cleanup failure")),
    )

    resolved = asyncio.run(
        auth_api.get_required_authenticated_user(request, Response(), SimpleNamespace())
    )

    assert resolved is user


def test_required_session_lookup_failure_is_not_masked(monkeypatch) -> None:
    settings = _auth_settings()
    request = _auth_request(settings)
    monkeypatch.setattr(
        auth_api,
        "get_user_by_session_token",
        AsyncMock(side_effect=SQLAlchemyError("synthetic lookup failure")),
    )

    with pytest.raises(SQLAlchemyError, match="synthetic lookup failure"):
        asyncio.run(
            auth_api.get_required_authenticated_user(request, Response(), SimpleNamespace())
        )


def test_oauth_callback_survives_cleanup_database_failure(monkeypatch) -> None:
    settings = _auth_settings()
    request = _auth_request(settings, with_session_cookie=False)
    user = User(id=uuid4(), github_user_id=1, github_login="synthetic-user")
    record = SimpleNamespace(
        encrypted_code_verifier=b"synthetic-ciphertext",
        encryption_nonce=b"0" * 12,
        redirect_path="/",
    )

    class Transaction:
        async def __aenter__(self) -> "Transaction":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

    class SessionStub:
        def begin(self) -> Transaction:
            return Transaction()

    class AuthClient:
        async def exchange_code(self, **kwargs: object) -> str:
            return "synthetic-provider-token"

    class GitHubClient:
        async def get_authenticated_user(self, access_token: str) -> GitHubUser:
            return GitHubUser.model_validate({
                "id": 1,
                "login": "synthetic-user",
                "name": None,
                "avatar_url": "https://avatars.example/user.png",
                "bio": None,
                "public_repos": 0,
                "followers": 0,
                "following": 0,
                "html_url": "https://github.com/synthetic-user",
                "created_at": "2025-01-01T00:00:00Z",
            })

    create_session = AsyncMock()
    monkeypatch.setattr(auth_api, "consume_login_state", AsyncMock(return_value=record))
    monkeypatch.setattr(auth_api, "decrypt_verifier", lambda *args: "synthetic-verifier")
    monkeypatch.setattr(auth_api, "upsert_user", AsyncMock(return_value=user))
    monkeypatch.setattr(auth_api, "create_session", create_session)
    monkeypatch.setattr(
        auth_api,
        "get_session_factory",
        lambda _: (_ for _ in ()).throw(SQLAlchemyError("synthetic cleanup failure")),
    )

    response = asyncio.run(
        auth_api.github_callback(
            request,
            code="synthetic-code",
            state="synthetic-state",
            session=SessionStub(),
            auth_client=AuthClient(),
            github_client=GitHubClient(),
        )
    )

    assert response.status_code == 303
    assert response.headers["location"].endswith("/")
    assert "devlens_session=" in response.headers["set-cookie"]
    create_session.assert_awaited_once()
