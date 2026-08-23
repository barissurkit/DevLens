import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.db.repositories.analysis_snapshots import SnapshotPayloadValidationError
from app.services import analysis_snapshot_cache as cache_module
from app.services.analysis_snapshot_cache import (
    AnalysisSnapshotCacheService,
    CachedAnalysis,
)

from test_analysis_endpoint import create_result


class _SessionContext:
    def __init__(self, repository=None) -> None:
        self.repository = repository

    async def __aenter__(self):
        return self

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        return None


def test_cache_disabled_at_zero_without_session_factory() -> None:
    called = False

    def provider(settings):
        nonlocal called
        called = True
        raise AssertionError("cache must not create a session")

    service = AnalysisSnapshotCacheService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test", analysis_cache_ttl_seconds=0),
        session_factory_provider=provider,
    )

    assert asyncio.run(service.get_fresh_analysis(username="octocat", request_kind="analysis")) is None
    assert called is False


def test_cache_returns_validated_analysis_and_original_timestamp(monkeypatch) -> None:
    analysis = create_result()
    generated_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    class Repository:
        async def get_latest_compatible_analysis(self, **kwargs):
            return type(
                "Record",
                (),
                {"analysis": analysis, "analysis_generated_at": generated_at},
            )()

    monkeypatch.setattr(cache_module, "AnalysisSnapshotRepository", lambda session: Repository())
    service = AnalysisSnapshotCacheService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: _SessionContext(),
    )

    result = asyncio.run(service.get_fresh_analysis(username="octocat", request_kind="analysis"))

    assert isinstance(result, CachedAnalysis)
    assert result.analysis is analysis
    assert result.analysis_generated_at == generated_at


def test_cache_operational_read_failure_is_miss(monkeypatch) -> None:
    class Repository:
        async def get_latest_compatible_analysis(self, **kwargs):
            raise OperationalError("synthetic", {}, RuntimeError("down"))

    monkeypatch.setattr(cache_module, "AnalysisSnapshotRepository", lambda session: Repository())
    service = AnalysisSnapshotCacheService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: _SessionContext(),
    )

    assert asyncio.run(service.get_fresh_analysis(username="octocat", request_kind="analysis")) is None


def test_cache_corrupt_payload_is_miss(monkeypatch) -> None:
    class Repository:
        async def get_latest_compatible_analysis(self, **kwargs):
            raise SnapshotPayloadValidationError("corrupt")

    monkeypatch.setattr(cache_module, "AnalysisSnapshotRepository", lambda session: Repository())
    service = AnalysisSnapshotCacheService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: _SessionContext(),
    )

    assert asyncio.run(service.get_fresh_analysis(username="octocat", request_kind="analysis")) is None


def test_unexpected_cache_error_is_not_swallowed(monkeypatch) -> None:
    class Repository:
        async def get_latest_compatible_analysis(self, **kwargs):
            raise RuntimeError("programmer bug")

    monkeypatch.setattr(cache_module, "AnalysisSnapshotRepository", lambda session: Repository())
    service = AnalysisSnapshotCacheService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: _SessionContext(),
    )

    with pytest.raises(RuntimeError, match="programmer bug"):
        asyncio.run(service.get_fresh_analysis(username="octocat", request_kind="analysis"))
