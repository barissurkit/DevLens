from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.action_plan import require_workspace_origin
from app.api.auth import get_required_authenticated_user
from app.db.database import get_session
from app.db.models import SavedProfile, User
from app.db.repositories.saved_profiles import (
    SAVED_PROFILES_MAX,
    LatestAnalysis,
    SavedProfilesLimitReachedError,
    delete_saved_profile,
    latest_analyses,
    list_saved_profiles,
    save_profile,
)
from app.schemas.saved_profile import SavedProfileCreate, SavedProfileResponse, SavedProfilesResponse

router = APIRouter(prefix="/api/v1/workspace/saved-profiles", tags=["Saved Profiles"])


async def require_user(request: Request, response: Response, session: AsyncSession = Depends(get_session)) -> User:
    return await get_required_authenticated_user(request, response, session)


def to_response(profile: SavedProfile, latest: dict[str, LatestAnalysis]) -> SavedProfileResponse:
    found = latest.get(profile.github_username_normalized)
    return SavedProfileResponse(
        id=profile.id,
        username=profile.github_username,
        saved_at=profile.created_at,
        latest_score=found.score if found else None,
        latest_analyzed_at=found.analyzed_at if found else None,
    )


@router.get("", response_model=SavedProfilesResponse)
async def get_saved_profiles(user: User = Depends(require_user), session: AsyncSession = Depends(get_session)) -> SavedProfilesResponse:
    profiles = await list_saved_profiles(session, user.id)
    latest = await latest_analyses(session, [profile.github_username_normalized for profile in profiles])
    return SavedProfilesResponse(profiles=[to_response(profile, latest) for profile in profiles], limit=SAVED_PROFILES_MAX)


@router.post("", response_model=SavedProfileResponse)
async def create_saved_profile(
    payload: SavedProfileCreate,
    request: Request,
    response: Response,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> SavedProfileResponse:
    require_workspace_origin(request, origin, content_type)
    try:
        profile, created = await save_profile(session, user.id, payload.username)
    except SavedProfilesLimitReachedError:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "saved_profiles_limit_reached",
                "message": f"En fazla {SAVED_PROFILES_MAX} profil kaydedebilirsin. Yeni eklemek için birini kaldır.",
            },
        ) from None
    await session.commit()
    await session.refresh(profile)
    response.status_code = 201 if created else 200
    latest = await latest_analyses(session, [profile.github_username_normalized])
    return to_response(profile, latest)


@router.delete("/{profile_id}", status_code=204)
async def remove_saved_profile(
    profile_id: UUID,
    request: Request,
    origin: str | None = Header(default=None),
    content_type: str | None = Header(default=None),
    user: User = Depends(require_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    require_workspace_origin(request, origin, content_type)
    if not await delete_saved_profile(session, user.id, profile_id):
        raise HTTPException(status_code=404, detail="Saved profile not found.")
    await session.commit()
