"""Permanent PostgreSQL regression coverage for the final persistence/cache contract.

These tests intentionally require a disposable database selected through
DEVLENS_TEST_DATABASE_URL. They never migrate or mutate DATABASE_URL.
"""

import asyncio
import os
from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.ext.asyncio import create_async_engine

import app.api.analysis as analysis_api
import app.api.interpretation as interpretation_api
from app.api.github import (
    get_analysis_snapshot_cache_service,
    get_gemini_client,
    get_github_client,
    get_snapshot_persistence_service,
)
from app.config import Settings
from app.db.constants import ANALYSIS_ENGINE_VERSION, ANALYSIS_SNAPSHOT_SCHEMA_VERSION
from app.db.database import create_session_factory, dispose_engine, get_engine
from app.db.models import AnalysisSnapshot
from app.db.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.main import app
from app.schemas.interpretation import (
    InterpretationUnavailableReason,
    PortfolioInterpretationResult,
)
from app.services.analysis_snapshot_cache import AnalysisSnapshotCacheService
from app.services.analysis_snapshot_persistence import AnalysisSnapshotPersistenceService
from app.services.portfolio_interpretation_composition import PortfolioInterpretationCompositionResult
from test_analysis_endpoint import create_result


TEST_DATABASE_URL = os.getenv("DEVLENS_TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not TEST_DATABASE_URL,
        reason="DEVLENS_TEST_DATABASE_URL is required for final PostgreSQL integration tests",
    ),
]


@pytest.fixture
def database_url() -> str:
    assert TEST_DATABASE_URL is not None
    return TEST_DATABASE_URL


@pytest.fixture
def runtime(database_url: str) -> Iterator[SimpleNamespace]:
    settings = Settings(
        _env_file=None,
        database_url=database_url,
        analysis_cache_ttl_seconds=900,
    )
    cache = AnalysisSnapshotCacheService(settings)
    persistence = AnalysisSnapshotPersistenceService(settings)
    app.dependency_overrides[get_analysis_snapshot_cache_service] = lambda: cache
    app.dependency_overrides[get_snapshot_persistence_service] = lambda: persistence
    yield SimpleNamespace(settings=settings, cache=cache, persistence=persistence)
    app.dependency_overrides.clear()


async def _rows(database_url: str, username: str) -> list[AnalysisSnapshot]:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            result = await session.execute(
                select(AnalysisSnapshot)
                .where(AnalysisSnapshot.github_username_normalized == username)
                .order_by(AnalysisSnapshot.created_at, AnalysisSnapshot.id)
            )
            return list(result.scalars().all())
    finally:
        await engine.dispose()


async def _delete_user(database_url: str, username: str) -> None:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    sessions = create_session_factory(engine)
    try:
        async with sessions() as session:
            async with session.begin():
                await session.execute(
                    delete(AnalysisSnapshot).where(
                        AnalysisSnapshot.github_username_normalized == username
                    )
                )
    finally:
        await engine.dispose()


async def _request(path: str, payload: dict[str, str]) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=payload)


def _set_analysis_service(monkeypatch, result, calls: list[str]) -> None:
    async def run(*, username: str, client) -> object:
        calls.append(username)
        return result

    monkeypatch.setattr(analysis_api, "run_github_portfolio_analysis", run)
    app.dependency_overrides[get_github_client] = lambda: object()


def test_migrated_schema_has_single_final_cache_shape(database_url: str) -> None:
    async def scenario() -> None:
        engine = create_async_engine(database_url, pool_pre_ping=True)
        try:
            async with engine.connect() as connection:
                columns = await connection.run_sync(
                    lambda sync: {column["name"] for column in inspect(sync).get_columns("analysis_snapshots")}
                )
                indexes = await connection.run_sync(
                    lambda sync: {index["name"] for index in inspect(sync).get_indexes("analysis_snapshots")}
                )
                heads = await connection.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                assert {row[0] for row in heads} == {"20260828_03"}
                assert {
                    "id", "github_username", "github_username_normalized",
                    "analysis_schema_version", "analysis_engine_version",
                    "interpretation_schema_version", "analysis_payload",
                    "interpretation_payload", "analysis_generated_at", "created_at",
                } <= columns
                assert {
                    "ix_analysis_snapshots_username_created_at",
                    "ix_analysis_snapshots_analysis_cache",
                } <= indexes
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_cold_warm_analysis_and_process_restart_reuse(
    database_url: str, runtime: SimpleNamespace, monkeypatch
) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "synthetic-user")
        result = create_result()
        calls: list[str] = []
        _set_analysis_service(monkeypatch, result, calls)

        cold = await _request("/api/v1/analysis", {"username": "synthetic-user"})
        assert cold.status_code == 200
        assert cold.json() == result.model_dump(mode="json")
        assert len(calls) == 1
        assert len(await _rows(database_url, "synthetic-user")) == 1

        warm = await _request("/api/v1/analysis", {"username": "SYNTHETIC-USER"})
        assert warm.status_code == 200
        assert len(calls) == 1
        assert len(await _rows(database_url, "synthetic-user")) == 1

        await dispose_engine(get_engine(database_url))
        get_engine.cache_clear()
        restarted_settings = Settings(_env_file=None, database_url=database_url)
        app.dependency_overrides[get_analysis_snapshot_cache_service] = lambda: AnalysisSnapshotCacheService(restarted_settings)
        app.dependency_overrides[get_snapshot_persistence_service] = lambda: AnalysisSnapshotPersistenceService(restarted_settings)
        after_restart = await _request("/api/v1/analysis", {"username": "synthetic-user"})
        assert after_restart.status_code == 200
        assert len(calls) == 1

    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.clear()
        get_engine.cache_clear()


def test_warm_interpretation_runs_ai_again_and_writes_composite_snapshots(
    database_url: str, runtime: SimpleNamespace, monkeypatch
) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "synthetic-user")
        result = create_result()
        analysis_calls: list[str] = []
        _set_analysis_service(monkeypatch, result, analysis_calls)
        gemini_calls: list[int] = []

        async def interpret(*, analysis, client):
            gemini_calls.append(1)
            return PortfolioInterpretationResult(
                available=False,
                reason=InterpretationUnavailableReason.INSUFFICIENT_EVIDENCE,
            )

        monkeypatch.setattr(interpretation_api, "interpret_github_portfolio", interpret)
        async def compose(*, username, github_client, gemini_client):
            return PortfolioInterpretationCompositionResult(
                analysis=result,
                interpretation=await interpret(analysis=result, client=gemini_client),
            )

        monkeypatch.setattr(interpretation_api, "analyze_and_interpret_github_portfolio", compose)
        app.dependency_overrides[get_gemini_client] = lambda: object()

        first = await _request("/api/v1/interpretation", {"username": "synthetic-user"})
        second = await _request("/api/v1/interpretation", {"username": "synthetic-user"})
        assert first.status_code == second.status_code == 200
        assert len(analysis_calls) == 0
        assert len(gemini_calls) == 2
        rows = await _rows(database_url, "synthetic-user")
        assert len(rows) == 2
        assert all(row.interpretation_payload is not None for row in rows)
        assert rows[1].analysis_generated_at == rows[0].analysis_generated_at
        await dispose_engine(get_engine(database_url))
        get_engine.cache_clear()

    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.clear()


def test_concurrent_warm_analysis_isolated_and_does_not_write_duplicates(
    database_url: str, runtime: SimpleNamespace, monkeypatch
) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "synthetic-user")
        result = create_result()
        calls: list[str] = []
        _set_analysis_service(monkeypatch, result, calls)
        assert (await _request("/api/v1/analysis", {"username": "synthetic-user"})).status_code == 200

        async def send() -> httpx.Response:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                return await client.post("/api/v1/analysis", json={"username": "synthetic-user"})

        responses = await asyncio.gather(*(send() for _ in range(5)))
        assert all(response.status_code == 200 for response in responses)
        assert len(calls) == 1
        assert len(await _rows(database_url, "synthetic-user")) == 1
        await dispose_engine(get_engine(database_url))
        get_engine.cache_clear()

    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.clear()


def test_compatible_candidate_selection_and_stale_policy(database_url: str) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "candidate-user")
        engine = create_async_engine(database_url, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        now = datetime.now(timezone.utc)
        try:
            async with sessions() as session:
                async with session.begin():
                    repo = AnalysisSnapshotRepository(session)
                    await repo.create(
                        github_username="candidate-user",
                        analysis=create_result(),
                        analysis_generated_at=now - timedelta(minutes=1),
                        analysis_engine_version=ANALYSIS_ENGINE_VERSION,
                    )
                    await repo.create(
                        github_username="candidate-user",
                        analysis=create_result(),
                        analysis_generated_at=now,
                        analysis_engine_version="old-engine",
                    )
                candidate = await repo.get_latest_compatible_analysis(
                    username="candidate-user",
                    analysis_schema_version=ANALYSIS_SNAPSHOT_SCHEMA_VERSION,
                    analysis_engine_version=ANALYSIS_ENGINE_VERSION,
                    fresh_after=now - timedelta(minutes=15),
                )
                assert candidate is not None
                assert candidate.analysis_generated_at >= now - timedelta(minutes=15)
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_transaction_failure_does_not_rollback_independent_write(database_url: str) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "isolation-a")
        await _delete_user(database_url, "isolation-b")
        engine = create_async_engine(database_url, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        try:
            async with sessions() as failed:
                with pytest.raises(RuntimeError):
                    async with failed.begin():
                        await AnalysisSnapshotRepository(failed).create(
                            github_username="isolation-a", analysis=create_result()
                        )
                        raise RuntimeError("forced rollback")
            async with sessions() as successful:
                async with successful.begin():
                    await AnalysisSnapshotRepository(successful).create(
                        github_username="isolation-b", analysis=create_result()
                    )
            assert await _rows(database_url, "isolation-a") == []
            assert len(await _rows(database_url, "isolation-b")) == 1
        finally:
            await engine.dispose()

    asyncio.run(scenario())


def test_ttl_zero_skips_cache_reads_and_still_persists(database_url: str, monkeypatch) -> None:
    async def scenario() -> None:
        await _delete_user(database_url, "ttl-user")
        settings = Settings(_env_file=None, database_url=database_url, analysis_cache_ttl_seconds=0)
        cache = AnalysisSnapshotCacheService(settings)
        persistence = AnalysisSnapshotPersistenceService(settings)
        app.dependency_overrides[get_analysis_snapshot_cache_service] = lambda: cache
        app.dependency_overrides[get_snapshot_persistence_service] = lambda: persistence
        result = create_result().model_copy(
            update={
                "user": create_result().user.model_copy(
                    update={"username": "ttl-user", "html_url": "https://github.com/ttl-user"}
                )
            }
        )
        calls: list[str] = []
        _set_analysis_service(monkeypatch, result, calls)
        assert (await _request("/api/v1/analysis", {"username": "ttl-user"})).status_code == 200
        assert (await _request("/api/v1/analysis", {"username": "ttl-user"})).status_code == 200
        assert len(calls) == 2
        assert len(await _rows(database_url, "ttl-user")) == 2
        await dispose_engine(get_engine(database_url))
        get_engine.cache_clear()

    try:
        asyncio.run(scenario())
    finally:
        app.dependency_overrides.clear()
