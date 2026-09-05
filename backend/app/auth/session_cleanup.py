from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from sqlalchemy.exc import SQLAlchemyError

from app.db.database import DatabaseNotConfiguredError

SESSION_CLEANUP_INTERVAL_SECONDS = 300.0
SESSION_CLEANUP_BATCH_SIZE = 100


class SessionCleanupCoordinator:
    """Coordinate low-frequency, best-effort session cleanup per app process."""

    def __init__(self, monotonic: Callable[[], float] = time.monotonic) -> None:
        self._monotonic = monotonic
        self._last_attempt_at: float | None = None
        self._lock = asyncio.Lock()

    async def maybe_cleanup(
        self, cleanup: Callable[[], Awaitable[int]]
    ) -> int | None:
        async with self._lock:
            now = self._monotonic()
            if (
                self._last_attempt_at is not None
                and now - self._last_attempt_at < SESSION_CLEANUP_INTERVAL_SECONDS
            ):
                return None
            self._last_attempt_at = now

        try:
            return await cleanup()
        except (DatabaseNotConfiguredError, SQLAlchemyError, OSError):
            return None
