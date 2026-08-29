import base64
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Query, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.crypto import (
    AuthStateCryptoError,
    decode_encryption_key,
    decrypt_verifier,
    encrypt_verifier,
    random_urlsafe_token,
    sha256_digest,
)
from app.auth.provider import GitHubAuthClient, GitHubAuthError
from app.auth.repositories import (
    consume_login_state,
    create_session,
    delete_expired_login_states,
    delete_expired_sessions,
    delete_login_state,
    delete_session_by_token,
    get_user_by_session_token,
    upsert_user,
    utc_now,
)
from app.config import Settings, get_settings
from app.db.database import DatabaseNotConfiguredError, get_session, get_session_factory
from app.db.models import OAuthLoginState, User
from app.schemas.auth import AuthErrorResponse, MeResponse
from app.services.github.client import GitHubClient
from app.observability import emit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

STATE_TTL = timedelta(minutes=10)
SESSION_TTL = timedelta(days=30)
SESSION_COOKIE = "__Host-devlens_session"
DEV_SESSION_COOKIE = "devlens_session"


def _cookie_name(settings: Settings) -> str:
    return SESSION_COOKIE if settings.auth_cookie_secure else DEV_SESSION_COOKIE


def _safe_redirect_path(value: str | None) -> str:
    path = value or "/"
    parsed = urlsplit(path)
    if not path.startswith("/") or path.startswith("//") or parsed.scheme or parsed.netloc:
        raise ValueError("Redirect path must be relative.")
    return path


def _frontend_redirect(settings: Settings, *, error: str | None = None, path: str = "/") -> str:
    safe_path = _safe_redirect_path(path)
    separator = "&" if "?" in safe_path else "?"
    if error:
        safe_path = f"{safe_path}{separator}{urlencode({'auth_error': error})}"
    return f"{settings.auth_frontend_origin.rstrip('/')}{safe_path}"


def _configuration_error(settings: Settings) -> str | None:
    required = (
        settings.github_app_client_id,
        settings.github_app_client_secret,
        settings.github_app_callback_url,
        settings.auth_state_encryption_key,
    )
    return "Authentication is not configured." if not all(required) else None


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _set_session_cookie(response: Response, settings: Settings, token: str, max_age: int) -> None:
    response.set_cookie(
        key=_cookie_name(settings),
        value=token,
        max_age=max_age,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.set_cookie(
        key=_cookie_name(settings),
        value="",
        max_age=0,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite="lax",
        path="/",
    )


async def _safe_failure_redirect(settings: Settings, path: str = "/") -> RedirectResponse:
    return RedirectResponse(_frontend_redirect(settings, error="authentication_failed", path=path), status_code=303)


async def get_auth_github_client() -> GitHubAuthClient | None:
    try:
        return GitHubAuthClient(get_settings())
    except GitHubAuthError:
        return None


async def get_auth_github_api_client() -> GitHubClient:
    return GitHubClient(get_settings())


async def get_optional_authenticated_user(request: Request) -> User | None:
    """Resolve a session when present; public endpoints stay anonymous on bad sessions."""
    settings = get_settings()
    cookie = request.cookies.get(_cookie_name(settings))
    if not cookie or not settings.database_url:
        return None
    try:
        async with get_session_factory(settings)() as session:
            return await get_user_by_session_token(session, sha256_digest(cookie))
    except (DatabaseNotConfiguredError, SQLAlchemyError, OSError):
        return None


@router.get("/github")
async def begin_github_login(
    next_path: str | None = Query(default=None, alias="next"),
    session: AsyncSession = Depends(get_session),
) -> RedirectResponse:
    settings = get_settings()
    if _configuration_error(settings):
        return await _safe_failure_redirect(settings)
    try:
        redirect_path = _safe_redirect_path(next_path)
        key = decode_encryption_key(settings.auth_state_encryption_key or "")
    except (ValueError, AuthStateCryptoError):
        return await _safe_failure_redirect(settings)

    state = random_urlsafe_token(32)
    verifier = random_urlsafe_token(32)
    nonce, encrypted_verifier = encrypt_verifier(verifier, key)
    now = utc_now()
    async with session.begin():
        await delete_expired_login_states(session)
        session.add(
            OAuthLoginState(
                state_hash=sha256_digest(state),
                encrypted_code_verifier=encrypted_verifier,
                encryption_nonce=nonce,
                redirect_path=redirect_path,
                created_at=now,
                expires_at=now + STATE_TTL,
            )
        )
    query = urlencode(
        {
            "client_id": settings.github_app_client_id,
            "redirect_uri": settings.github_app_callback_url,
            "state": state,
            "code_challenge": _pkce_challenge(verifier),
            "code_challenge_method": "S256",
        }
    )
    emit_event(logger, "auth.login.started")
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{query}", status_code=302)


@router.get("/github/callback", responses={400: {"model": AuthErrorResponse}})
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    session: AsyncSession = Depends(get_session),
    auth_client: GitHubAuthClient | None = Depends(get_auth_github_client),
    github_client: GitHubClient = Depends(get_auth_github_api_client),
) -> RedirectResponse:
    settings = get_settings()
    if _configuration_error(settings) or not state or error or not code:
        emit_event(logger, "auth.callback.rejected", error_category="invalid_callback")
        return await _safe_failure_redirect(settings)
    record: OAuthLoginState | None = None
    try:
        if auth_client is None:
            raise GitHubAuthError("GitHub App is not configured.")
        key = decode_encryption_key(settings.auth_state_encryption_key or "")
        async with session.begin():
            record = await consume_login_state(session, sha256_digest(state))
            if record is None:
                raise AuthStateCryptoError("OAuth state is invalid or expired.")
            verifier = decrypt_verifier(record.encrypted_code_verifier, record.encryption_nonce, key)
            redirect_path = record.redirect_path
        access_token = await auth_client.exchange_code(
            code=code,
            redirect_uri=settings.github_app_callback_url or "",
            code_verifier=verifier,
        )
        github_user = await github_client.get_authenticated_user(access_token)
        async with session.begin():
            await delete_expired_sessions(session)
            old_cookie = request.cookies.get(_cookie_name(settings))
            if old_cookie:
                await delete_session_by_token(session, sha256_digest(old_cookie))
            user = await upsert_user(session, github_user)
            session_token = random_urlsafe_token(32)
            await create_session(session, user.id, sha256_digest(session_token), utc_now() + SESSION_TTL)
        redirect = RedirectResponse(_frontend_redirect(settings, path=redirect_path), status_code=303)
        _set_session_cookie(redirect, settings, session_token, int(SESSION_TTL.total_seconds()))
        emit_event(logger, "auth.login.succeeded")
        return redirect
    except (AuthStateCryptoError, GitHubAuthError, httpx.HTTPError, ValueError):
        if record is not None:
            try:
                async with session.begin():
                    await delete_login_state(session, record)
            except Exception:
                await session.rollback()
        emit_event(logger, "auth.login.failed", level=logging.WARNING, error_category="provider_or_state_error")
        return await _safe_failure_redirect(settings)


@router.get("/me", response_model=MeResponse)
async def me(
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    dev_session_cookie: str | None = Cookie(default=None, alias=DEV_SESSION_COOKIE),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    settings = get_settings()
    session_cookie = session_cookie or dev_session_cookie
    if not session_cookie:
        return MeResponse(authenticated=False, user=None)
    user = await get_user_by_session_token(session, sha256_digest(session_cookie))
    if user is None:
        _clear_session_cookie(response, settings)
        emit_event(logger, "auth.session.rejected", error_category="invalid_or_expired")
        return MeResponse(authenticated=False, user=None)
    return MeResponse(authenticated=True, user=user)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    origin: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    dev_session_cookie: str | None = Cookie(default=None, alias=DEV_SESSION_COOKIE),
    session: AsyncSession = Depends(get_session),
) -> None:
    settings = get_settings()
    session_cookie = session_cookie or dev_session_cookie
    if origin != settings.auth_frontend_origin:
        raise HTTPException(status_code=403, detail="Invalid request origin.")
    async with session.begin():
        if session_cookie:
            await delete_session_by_token(session, sha256_digest(session_cookie))
    _clear_session_cookie(response, settings)
    emit_event(logger, "auth.logout.completed")
