import asyncio

import pytest
from sqlalchemy.exc import OperationalError

from app.config import Settings
from app.services import analysis_snapshot_persistence as persistence_module
from app.services.analysis_snapshot_persistence import (
    AnalysisSnapshotPersistenceService,
    SnapshotPersistenceOutcome,
)

from test_analysis_endpoint import create_result


class _Transaction:
    def __init__(self) -> None:
        self.rolled_back = False

    async def __aenter__(self) -> "_Transaction":
        return self

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        self.rolled_back = exception_type is not None


class _Session:
    def __init__(self) -> None:
        self.transaction = _Transaction()

    async def __aenter__(self) -> "_Session":
        return self

    async def __aexit__(self, exception_type, exception, traceback) -> None:
        return None

    def begin(self) -> _Transaction:
        return self.transaction


def test_unconfigured_database_skips_without_creating_session() -> None:
    provider_called = False

    def provider(settings: Settings):
        nonlocal provider_called
        provider_called = True
        raise AssertionError("session factory must not be created")

    service = AnalysisSnapshotPersistenceService(
        Settings(_env_file=None), session_factory_provider=provider
    )

    result = asyncio.run(service.persist(analysis=create_result(), request_kind="analysis"))

    assert result is SnapshotPersistenceOutcome.SKIPPED_NOT_CONFIGURED
    assert provider_called is False


def test_operational_error_is_fail_open_and_transaction_rolls_back(monkeypatch) -> None:
    session = _Session()

    class FailingRepository:
        def __init__(self, session) -> None:
            self.session = session

        async def create(self, **kwargs):
            raise OperationalError("synthetic", {}, RuntimeError("db down"))

    monkeypatch.setattr(persistence_module, "AnalysisSnapshotRepository", FailingRepository)
    service = AnalysisSnapshotPersistenceService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: session,
    )

    result = asyncio.run(service.persist(analysis=create_result(), request_kind="analysis"))

    assert result is SnapshotPersistenceOutcome.FAILED_OPERATIONAL
    assert session.transaction.rolled_back is True


def test_unexpected_programmer_error_is_not_swallowed(monkeypatch) -> None:
    class FailingRepository:
        def __init__(self, session) -> None:
            self.session = session

        async def create(self, **kwargs):
            raise RuntimeError("programmer bug")

    monkeypatch.setattr(persistence_module, "AnalysisSnapshotRepository", FailingRepository)
    service = AnalysisSnapshotPersistenceService(
        Settings(_env_file=None, database_url="postgresql+asyncpg://local/test"),
        session_factory_provider=lambda settings: lambda: _Session(),
    )

    with pytest.raises(RuntimeError, match="programmer bug"):
        asyncio.run(service.persist(analysis=create_result(), request_kind="analysis"))
