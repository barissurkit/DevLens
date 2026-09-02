import logging
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.db.database import DatabaseNotConfiguredError, get_session_factory
from app.db.models import User
from app.db.repositories.portfolio_history import capture_history
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
            async with self._session_factory_provider(self._settings)() as session:
                async with session.begin():
                    await capture_history(session, user, analysis)
            emit_event(logger, "history.capture.completed", result="persisted_or_deduplicated")
            return True
        except (DatabaseNotConfiguredError, IntegrityError, SQLAlchemyError, OSError) as exc:
            emit_event(logger, "history.capture.failed", level=logging.WARNING, result="failed_operational", error_category=type(exc).__name__)
            return False
