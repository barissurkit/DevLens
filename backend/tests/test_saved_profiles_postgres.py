import asyncio
import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.database import create_session_factory
from app.db.models import AnalysisSnapshot, SavedProfile, User
from app.db.repositories.saved_profiles import (
    SAVED_PROFILES_MAX,
    SavedProfilesLimitReachedError,
    delete_saved_profile,
    latest_analyses,
    list_saved_profiles,
    save_profile,
)

TEST_DATABASE_URL = os.getenv("DEVLENS_TEST_DATABASE_URL")
pytestmark = pytest.mark.integration


def run(scenario) -> None:
    if not TEST_DATABASE_URL:
        pytest.skip("DEVLENS_TEST_DATABASE_URL is required for real PostgreSQL tests")

    async def main() -> None:
        engine = create_async_engine(TEST_DATABASE_URL, pool_pre_ping=True)
        try:
            await scenario(create_session_factory(engine))
        finally:
            await engine.dispose()

    asyncio.run(main())


async def make_user(sessions) -> object:
    user_id = uuid4()
    async with sessions() as session:
        async with session.begin():
            session.add(User(id=user_id, github_user_id=uuid4().int % 2**63, github_login=f"sp-{str(user_id)[:8]}"))
    return user_id


def snapshot(username: str, score, created_at: datetime, *, payload: dict | None = None) -> AnalysisSnapshot:
    return AnalysisSnapshot(
        github_username=username,
        github_username_normalized=username.lower(),
        analysis_schema_version="t",
        analysis_engine_version="t",
        analysis_payload=payload if payload is not None else {"score": {"overall_score": score}},
        analysis_generated_at=created_at,
        created_at=created_at,
    )


def test_a_profile_is_saved_once_whatever_its_case_and_listed_newest_first() -> None:
    async def scenario(sessions) -> None:
        user_id = await make_user(sessions)
        # Each save is its own request (and transaction), as it is in the application.
        async with sessions() as session:
            async with session.begin():
                first, created_first = await save_profile(session, user_id, "Octocat")
        async with sessions() as session:
            async with session.begin():
                again, created_again = await save_profile(session, user_id, "octocat")
        async with sessions() as session:
            async with session.begin():
                await save_profile(session, user_id, "torvalds")
        assert (created_first, created_again) == (True, False)
        assert again.id == first.id and first.github_username == "Octocat"

        async with sessions() as session:
            listed = await list_saved_profiles(session, user_id)
        assert [item.github_username for item in listed] == ["torvalds", "Octocat"]

    run(scenario)


def test_the_cap_is_enforced_and_removing_one_makes_room() -> None:
    async def scenario(sessions) -> None:
        user_id = await make_user(sessions)
        async with sessions() as session:
            async with session.begin():
                for index in range(SAVED_PROFILES_MAX):
                    await save_profile(session, user_id, f"user{index}")
        async with sessions() as session:
            with pytest.raises(SavedProfilesLimitReachedError):
                async with session.begin():
                    await save_profile(session, user_id, "one-too-many")
        async with sessions() as session:
            async with session.begin():
                listed = await list_saved_profiles(session, user_id)
                assert await delete_saved_profile(session, user_id, listed[0].id) is True
                await save_profile(session, user_id, "one-too-many")
            assert len(await list_saved_profiles(session, user_id)) == SAVED_PROFILES_MAX

    run(scenario)


def test_one_person_cannot_remove_or_see_another_persons_saved_profile() -> None:
    async def scenario(sessions) -> None:
        owner, other = await make_user(sessions), await make_user(sessions)
        async with sessions() as session:
            async with session.begin():
                profile, _ = await save_profile(session, owner, "octocat")
        async with sessions() as session:
            async with session.begin():
                assert await delete_saved_profile(session, other, profile.id) is False
                assert await list_saved_profiles(session, other) == []
        async with sessions() as session:
            assert len(await list_saved_profiles(session, owner)) == 1
        # The same login can be saved by the other person independently.
        async with sessions() as session:
            async with session.begin():
                await save_profile(session, other, "octocat")
        async with sessions() as session:
            assert len(await list_saved_profiles(session, other)) == 1

    run(scenario)


def test_the_latest_stored_analysis_gives_the_score_and_missing_ones_are_left_out() -> None:
    async def scenario(sessions) -> None:
        name = f"lat{uuid4().hex[:10]}"
        unscored = f"uns{uuid4().hex[:10]}"
        never = f"nev{uuid4().hex[:10]}"
        now = datetime.now(timezone.utc)
        async with sessions() as session:
            async with session.begin():
                session.add_all([
                    snapshot(name, 31, now - timedelta(days=5)),
                    snapshot(name.upper(), 47, now - timedelta(days=1)),  # normalised to the same key, newest
                    snapshot(unscored, None, now, payload={"score": {"overall_score": None}}),
                ])
            found = await latest_analyses(session, [name.lower(), unscored.lower(), never.lower()])

        assert found[name.lower()].score == 47
        assert found[unscored.lower()].score is None
        assert never.lower() not in found

    run(scenario)


def test_deleting_the_person_removes_their_saved_profiles() -> None:
    async def scenario(sessions) -> None:
        user_id = await make_user(sessions)
        async with sessions() as session:
            async with session.begin():
                await save_profile(session, user_id, "octocat")
        async with sessions() as session:
            async with session.begin():
                user = await session.get(User, user_id)
                await session.delete(user)
            remaining = await session.execute(select(SavedProfile).where(SavedProfile.user_id == user_id))
            assert remaining.scalars().all() == []

    run(scenario)
