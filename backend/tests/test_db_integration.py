import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.database import create_session_factory
from app.db.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.schemas.analysis import (
    PortfolioRepositoryAnalysis,
    PortfolioRepositorySelection,
)
from test_analysis_endpoint import create_result
from test_portfolio_aggregation import create_failure, create_result as create_repository_result

TEST_DATABASE_URL = os.getenv("DEVLENS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


def test_postgresql_snapshot_round_trip_and_rollback() -> None:
    if not TEST_DATABASE_URL:
        pytest.skip("DEVLENS_TEST_DATABASE_URL is required for real PostgreSQL tests")

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        analysis = create_result()
        async with sessions() as session:
            async with session.begin():
                repository = AnalysisSnapshotRepository(session)
                created = await repository.create(
                    github_username=" OctoCat ", analysis=analysis
                )
                assert created.interpretation is None
            latest = await repository.get_latest_by_username("OCTOCAT")
            assert latest is not None
            assert latest.analysis.model_dump(mode="json") == analysis.model_dump(mode="json")
            assert latest.created_at.tzinfo is not None
            assert await repository.get_latest_by_username("missing") is None

        async with sessions() as session:
            with pytest.raises(RuntimeError):
                async with session.begin():
                    await AnalysisSnapshotRepository(session).create(
                        github_username="rollback-user", analysis=analysis
                    )
                    raise RuntimeError("forced rollback")
            assert await AnalysisSnapshotRepository(session).get_latest_by_username(
                "rollback-user"
            ) is None
        await engine.dispose()

    asyncio.run(scenario())


def test_postgresql_partial_portfolio_round_trip() -> None:
    if not TEST_DATABASE_URL:
        pytest.skip("DEVLENS_TEST_DATABASE_URL is required for real PostgreSQL tests")

    async def scenario() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        sessions = create_session_factory(engine)
        base = create_result()
        successful = create_repository_result("successful", overall_score=72)
        failed = create_failure("failed")
        partial_repository_analysis = PortfolioRepositoryAnalysis(
            selection_version="v1",
            repositories=[successful],
            failures=[failed],
            has_failures=True,
        )
        partial = base.model_copy(
            deep=True,
            update={
                "selection": PortfolioRepositorySelection(
                    version="v1",
                    selected=[successful.repository, failed.repository],
                    excluded=[],
                ),
                "repository_analysis": partial_repository_analysis,
                "aggregation": base.aggregation.model_copy(
                    update={
                        "selected_repository_count": 2,
                        "successful_repository_count": 1,
                        "failed_repository_count": 1,
                        "has_failures": True,
                    }
                ),
                "score": base.score.model_copy(
                    update={"is_available": True, "overall_score": 72, "is_partial": True}
                ),
            },
        )
        async with sessions() as session:
            async with session.begin():
                await AnalysisSnapshotRepository(session).create(
                    github_username="partial-user", analysis=partial
                )
            loaded = await AnalysisSnapshotRepository(session).get_latest_by_username(
                "PARTIAL-USER"
            )
            assert loaded is not None
            assert loaded.analysis.repository_analysis.has_failures is True
            assert loaded.analysis.aggregation.successful_repository_count == 1
            assert loaded.analysis.aggregation.failed_repository_count == 1
            assert loaded.analysis.repository_analysis.repositories[0].repository.name == "successful"
            failure = loaded.analysis.repository_analysis.failures[0]
            assert failure.repository.name == "failed"
            assert failure.code.value == "github_timeout"
            assert failure.message == "GitHub request timed out during repository analysis."
            assert loaded.analysis.score.overall_score == 72
            assert "/home/" not in loaded.analysis.model_dump_json()
        await engine.dispose()

    asyncio.run(scenario())
