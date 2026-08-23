import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.constants import ANALYSIS_ENGINE_VERSION, ANALYSIS_SNAPSHOT_SCHEMA_VERSION
from app.db.database import DatabaseNotConfiguredError, get_session_factory
from app.db.repositories.analysis_snapshots import (
    AnalysisSnapshotRepository,
    SnapshotPayloadValidationError,
)
from app.schemas.analysis import GitHubPortfolioAnalysis

logger = logging.getLogger(__name__)

SessionFactoryProvider = Callable[[Settings], async_sessionmaker[AsyncSession]]


@dataclass(frozen=True)
class CachedAnalysis:
    analysis: GitHubPortfolioAnalysis
    analysis_generated_at: datetime


class AnalysisSnapshotCacheService:
    def __init__(
        self,
        settings: Settings | None = None,
        session_factory_provider: SessionFactoryProvider = get_session_factory,
    ) -> None:
        self._settings = settings or get_settings()
        self._session_factory_provider = session_factory_provider

    async def get_fresh_analysis(self, *, username: str, request_kind: str) -> CachedAnalysis | None:
        if not self._settings.database_url or self._settings.analysis_cache_ttl_seconds == 0:
            return None

        fresh_after = datetime.now(timezone.utc) - timedelta(
            seconds=self._settings.analysis_cache_ttl_seconds
        )
        try:
            session_factory = self._session_factory_provider(self._settings)
            async with session_factory() as session:
                record = await AnalysisSnapshotRepository(session).get_latest_compatible_analysis(
                    username=username,
                    analysis_schema_version=ANALYSIS_SNAPSHOT_SCHEMA_VERSION,
                    analysis_engine_version=ANALYSIS_ENGINE_VERSION,
                    fresh_after=fresh_after,
                )
        except (
            DatabaseNotConfiguredError,
            SQLAlchemyError,
            OSError,
            SnapshotPayloadValidationError,
        ) as exc:
            logger.warning(
                "analysis cache lookup failed",
                extra={"request_kind": request_kind, "exception_type": type(exc).__name__},
            )
            return None

        if record is None:
            return None
        return CachedAnalysis(
            analysis=record.analysis,
            analysis_generated_at=record.analysis_generated_at,
        )
