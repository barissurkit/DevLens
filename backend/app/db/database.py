from collections.abc import AsyncIterator
from functools import lru_cache

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import Settings, get_settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised only when persistence is explicitly used without DATABASE_URL."""


def create_database_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@lru_cache(maxsize=1)
def get_engine(database_url: str | None = None) -> AsyncEngine:
    configured_url = database_url or get_settings().database_url
    if not configured_url:
        raise DatabaseNotConfiguredError(
            "DATABASE_URL is required to use the snapshot repository."
        )
    return create_database_engine(configured_url)


def get_session_factory(settings: Settings | None = None) -> async_sessionmaker[AsyncSession]:
    configured_settings = settings or get_settings()
    return create_session_factory(get_engine(configured_settings.database_url))


async def dispose_engine(engine: AsyncEngine) -> None:
    await engine.dispose()


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with get_session_factory(request.app.state.settings)() as session:
        yield session
