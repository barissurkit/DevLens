import logging
import time
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.database import DatabaseNotConfiguredError, get_session_factory
from app.db.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PublicPortfolioInterpretationResult
from app.observability import emit_event

logger = logging.getLogger(__name__)


class SnapshotPersistenceOutcome(StrEnum):
    PERSISTED = "persisted"
    SKIPPED_NOT_CONFIGURED = "skipped_not_configured"
    FAILED_OPERATIONAL = "failed_operational"


SessionFactoryProvider = Callable[[Settings], async_sessionmaker[AsyncSession]]


class AnalysisSnapshotPersistenceService:
    """Best-effort writer for immutable public analysis snapshots."""

    def __init__(
        self,
        settings: Settings | None = None,
        session_factory_provider: SessionFactoryProvider = get_session_factory,
    ) -> None:
        self._settings = settings or get_settings()
        self._session_factory_provider = session_factory_provider

    async def persist(
        self,
        *,
        analysis: GitHubPortfolioAnalysis,
        interpretation: PublicPortfolioInterpretationResult | None = None,
        analysis_generated_at: datetime | None = None,
        request_kind: str,
    ) -> SnapshotPersistenceOutcome:
        if not self._settings.database_url:
            emit_event(
                logger,
                "snapshot.write.skipped",
                operation=request_kind,
                result="not_configured",
            )
            return SnapshotPersistenceOutcome.SKIPPED_NOT_CONFIGURED

        started_at = time.monotonic()
        try:
            session_factory = self._session_factory_provider(self._settings)
            async with session_factory() as session:
                async with session.begin():
                    await AnalysisSnapshotRepository(session).create(
                        github_username=analysis.user.username,
                        analysis=analysis,
                        interpretation=interpretation,
                        analysis_generated_at=analysis_generated_at,
                    )
        except DatabaseNotConfiguredError:
            emit_event(
                logger,
                "snapshot.write.skipped",
                operation=request_kind,
                result="not_configured",
            )
            return SnapshotPersistenceOutcome.SKIPPED_NOT_CONFIGURED
        except SQLAlchemyError as exc:
            emit_event(
                logger,
                "snapshot.write_failed",
                level=logging.WARNING,
                operation=request_kind,
                duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
                result="failed_operational",
                error_category=type(exc).__name__,
            )
            return SnapshotPersistenceOutcome.FAILED_OPERATIONAL
        except OSError as exc:
            emit_event(
                logger,
                "snapshot.write_failed",
                level=logging.WARNING,
                operation=request_kind,
                duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
                result="failed_operational",
                error_category=type(exc).__name__,
            )
            return SnapshotPersistenceOutcome.FAILED_OPERATIONAL

        emit_event(
            logger,
            "snapshot.write.completed",
            operation=request_kind,
            duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
            result="persisted",
        )
        return SnapshotPersistenceOutcome.PERSISTED
