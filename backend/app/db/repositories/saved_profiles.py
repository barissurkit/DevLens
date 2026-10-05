from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AnalysisSnapshot, SavedProfile, User
from app.db.normalization import normalize_github_username

SAVED_PROFILES_MAX = 50


class SavedProfilesLimitReachedError(Exception):
    """Raised when a person already keeps the maximum number of saved profiles."""


@dataclass(frozen=True, slots=True)
class LatestAnalysis:
    score: int | None
    analyzed_at: datetime


async def list_saved_profiles(session: AsyncSession, user_id: UUID) -> list[SavedProfile]:
    result = await session.execute(
        select(SavedProfile)
        .where(SavedProfile.user_id == user_id)
        .order_by(SavedProfile.created_at.desc(), SavedProfile.id.desc())
    )
    return list(result.scalars())


async def latest_analyses(session: AsyncSession, normalized_usernames: list[str]) -> dict[str, LatestAnalysis]:
    """The newest stored analysis of each username (one query); usernames without one are left out."""

    if not normalized_usernames:
        return {}
    score = AnalysisSnapshot.analysis_payload["score"]["overall_score"].astext
    result = await session.execute(
        select(AnalysisSnapshot.github_username_normalized, score, AnalysisSnapshot.analysis_generated_at)
        .where(AnalysisSnapshot.github_username_normalized.in_(normalized_usernames))
        .distinct(AnalysisSnapshot.github_username_normalized)
        .order_by(AnalysisSnapshot.github_username_normalized, AnalysisSnapshot.created_at.desc())
    )
    found: dict[str, LatestAnalysis] = {}
    for username, raw_score, generated_at in result.all():
        try:
            parsed = int(raw_score) if raw_score is not None else None
        except ValueError:
            parsed = None
        found[username] = LatestAnalysis(score=parsed, analyzed_at=generated_at)
    return found


async def save_profile(session: AsyncSession, user_id: UUID, username: str) -> tuple[SavedProfile, bool]:
    """Saves a profile for the person; saving the same one again is a no-op. Returns it and whether it is new."""

    owner = await session.execute(select(User.id).where(User.id == user_id).with_for_update())
    if owner.scalar_one_or_none() is None:
        raise LookupError("Authenticated profile owner was not found.")

    normalized = normalize_github_username(username)
    existing = await session.execute(
        select(SavedProfile).where(SavedProfile.user_id == user_id, SavedProfile.github_username_normalized == normalized)
    )
    found = existing.scalar_one_or_none()
    if found is not None:
        return found, False

    count = await session.scalar(select(func.count(SavedProfile.id)).where(SavedProfile.user_id == user_id))
    if (count or 0) >= SAVED_PROFILES_MAX:
        raise SavedProfilesLimitReachedError

    profile = SavedProfile(user_id=user_id, github_username=username, github_username_normalized=normalized)
    session.add(profile)
    await session.flush()
    return profile, True


async def delete_saved_profile(session: AsyncSession, user_id: UUID, profile_id: UUID) -> bool:
    result = await session.execute(
        delete(SavedProfile).where(SavedProfile.id == profile_id, SavedProfile.user_id == user_id)
    )
    return result.rowcount == 1
