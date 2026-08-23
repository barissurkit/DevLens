import logging
from collections.abc import Callable
from enum import StrEnum

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.database import DatabaseNotConfiguredError, get_session_factory
from app.db.repositories.analysis_snapshots import AnalysisSnapshotRepository
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PublicPortfolioInterpretationResult

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
        request_kind: str,
    ) -> SnapshotPersistenceOutcome:
        if not self._settings.database_url:
            return SnapshotPersistenceOutcome.SKIPPED_NOT_CONFIGURED

        try:
            session_factory = self._session_factory_provider(self._settings)
            async with session_factory() as session:
                async with session.begin():
                    await AnalysisSnapshotRepository(session).create(
                        github_username=analysis.user.username,
                        analysis=analysis,
                        interpretation=interpretation,
                    )
        except DatabaseNotConfiguredError:
            return SnapshotPersistenceOutcome.SKIPPED_NOT_CONFIGURED
        except SQLAlchemyError as exc:
            logger.warning(
                "snapshot persistence failed",
                extra={
                    "request_kind": request_kind,
                    "exception_type": type(exc).__name__,
                },
            )
            return SnapshotPersistenceOutcome.FAILED_OPERATIONAL
        except OSError as exc:
            logger.warning(
                "snapshot persistence failed",
                extra={
                    "request_kind": request_kind,
                    "exception_type": type(exc).__name__,
                },
            )
            return SnapshotPersistenceOutcome.FAILED_OPERATIONAL

        return SnapshotPersistenceOutcome.PERSISTED
