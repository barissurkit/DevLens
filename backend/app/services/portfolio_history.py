import logging
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.database import DatabaseNotConfiguredError, get_session_factory
from app.db.models import PortfolioAnalysisHistory, User
from app.db.repositories.portfolio_history import capture_history, project_analysis
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.observability import emit_event

logger = logging.getLogger(__name__)
SessionFactoryProvider = Callable[[Settings], async_sessionmaker[AsyncSession]]


class PortfolioHistoryService:
    """Best-effort owner checkpoint writer; shared analysis remains independent."""

    def __init__(self, settings: Settings | None = None, session_factory_provider: SessionFactoryProvider = get_session_factory) -> None:
        self._settings = settings or get_settings()
        self._session_factory_provider = session_factory_provider

    async def capture(self, *, user: User, analysis: GitHubPortfolioAnalysis) -> bool:
        if not self._settings.database_url:
            return False
        try:
            projection = project_analysis(analysis)
            async with self._session_factory_provider(self._settings)() as session:
                async with session.begin():
                    await capture_history(session, user, analysis)
            emit_event(logger, "history.capture.completed", result="persisted_or_deduplicated")
            return True
        except IntegrityError:
            # A concurrent request may have committed the same unique checkpoint.
            # Verify that outcome in a fresh session instead of reporting a false failure.
            try:
                async with self._session_factory_provider(self._settings)() as verify_session:
                    existing = await verify_session.scalar(
                        select(PortfolioAnalysisHistory).where(
                            PortfolioAnalysisHistory.user_id == user.id,
                            PortfolioAnalysisHistory.analysis_fingerprint == projection.fingerprint,
                        )
                    )
                if existing is not None:
                    emit_event(logger, "history.capture.completed", result="deduplicated_concurrently")
                    return True
            except (DatabaseNotConfiguredError, SQLAlchemyError, OSError):
                pass
            emit_event(logger, "history.capture.failed", level=logging.WARNING, result="failed_operational", error_category="IntegrityError")
            return False
        except (AttributeError, TypeError, ValueError):
            emit_event(
                logger,
                "history.capture.failed",
                level=logging.WARNING,
                result="failed_operational",
                error_category="projection_error",
            )
            return False
        except (DatabaseNotConfiguredError, SQLAlchemyError, OSError) as exc:
            emit_event(logger, "history.capture.failed", level=logging.WARNING, result="failed_operational", error_category=type(exc).__name__)
            return False
