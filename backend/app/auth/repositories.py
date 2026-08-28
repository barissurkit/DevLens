from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import OAuthLoginState, Session, User
from app.schemas.github import GitHubUser


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def upsert_user(session: AsyncSession, github_user: GitHubUser) -> User:
    now = utc_now()
    result = await session.execute(
        select(User).where(User.github_user_id == github_user.github_user_id).with_for_update()
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            github_user_id=github_user.github_user_id,
            github_login=github_user.username,
            display_name=github_user.name,
            avatar_url=github_user.avatar_url,
            github_html_url=github_user.html_url,
            last_login_at=now,
        )
        session.add(user)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            result = await session.execute(
                select(User).where(User.github_user_id == github_user.github_user_id).with_for_update()
            )
            user = result.scalar_one()
    if user.github_login != github_user.username:
        user.github_login = github_user.username
    user.display_name = github_user.name
    user.avatar_url = github_user.avatar_url
    user.github_html_url = github_user.html_url
    user.last_login_at = now
    await session.flush()
    return user


async def create_session(session: AsyncSession, user_id: UUID, token_hash: bytes, expires_at: datetime) -> Session:
    record = Session(user_id=user_id, token_hash=token_hash, expires_at=expires_at)
    session.add(record)
    await session.flush()
    return record


async def get_user_by_session_token(session: AsyncSession, token_hash: bytes) -> User | None:
    result = await session.execute(
        select(User)
        .join(Session, Session.user_id == User.id)
        .where(Session.token_hash == token_hash, Session.expires_at > utc_now())
    )
    return result.scalar_one_or_none()


async def delete_session_by_token(session: AsyncSession, token_hash: bytes) -> None:
    await session.execute(delete(Session).where(Session.token_hash == token_hash))


async def delete_expired_sessions(session: AsyncSession) -> None:
    await session.execute(delete(Session).where(Session.expires_at <= utc_now()))


async def consume_login_state(session: AsyncSession, state_hash: bytes) -> OAuthLoginState | None:
    result = await session.execute(
        select(OAuthLoginState)
        .where(
            OAuthLoginState.state_hash == state_hash,
            OAuthLoginState.consumed_at.is_(None),
            OAuthLoginState.expires_at > utc_now(),
        )
        .with_for_update()
    )
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.consumed_at = utc_now()
    await session.flush()
    return record


async def delete_login_state(session: AsyncSession, record: OAuthLoginState) -> None:
    await session.delete(record)
    await session.flush()


async def delete_expired_login_states(session: AsyncSession) -> None:
    await session.execute(delete(OAuthLoginState).where(OAuthLoginState.expires_at <= utc_now()))
