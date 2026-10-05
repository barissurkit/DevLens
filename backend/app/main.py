import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.analysis import router as analysis_router
from app.api.badge import router as badge_router
from app.api.client_errors import router as client_errors_router
from app.api.github import router as github_router
from app.api.interpretation import router as interpretation_router
from app.api.auth import router as auth_router
from app.api.action_plan import router as action_plan_router
from app.api.ai_suggestions import router as ai_suggestions_router
from app.auth.session_cleanup import SessionCleanupCoordinator
from app.api.history import router as history_router
from app.api.saved_profiles import router as saved_profiles_router
from app.config import Settings, get_settings
from app.observability import REQUEST_ID, configure_logging, emit_event, new_request_id
from app.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str
    # Non-sensitive configuration flags so operators can spot a missing integration
    # (for example an unauthenticated GitHub client limited to 60 requests per hour).
    github_token_configured: bool | None = None
    ai_configured: bool | None = None
    database_configured: bool | None = None


def health_check(settings: Settings | None = None) -> HealthResponse:
    if settings is None:
        return HealthResponse(status="ok")
    return HealthResponse(
        status="ok",
        github_token_configured=bool(settings.github_token),
        ai_configured=settings.ai_configured,
        database_configured=bool(settings.database_url),
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    application_settings = settings or get_settings()
    application_settings.validate_runtime_configuration()
    application = FastAPI(title="DevLens API", version="0.1.0")
    application.state.settings = application_settings
    application.state.rate_limiter = RateLimiter()
    application.state.session_cleanup_coordinator = SessionCleanupCoordinator()

    @application.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = new_request_id()
        token = REQUEST_ID.set(request_id)
        started_at = time.monotonic()
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_path = getattr(route, "path", None)
            emit_event(
                logger,
                "request.completed",
                request_id=request_id,
                method=request.method,
                route=route_path if isinstance(route_path, str) else "unmatched",
                status_code=status_code,
                duration_ms=max(0, round((time.monotonic() - started_at) * 1000)),
            )
            if response is not None:
                response.headers["X-Request-ID"] = request_id
            REQUEST_ID.reset(token)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=application_settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["*"],
        # Cross-origin browsers hide non-safelisted response headers unless they are exposed;
        # the frontend reads Retry-After to tell users how long to wait after a 429.
        expose_headers=["Retry-After"],
    )
    application.include_router(github_router)
    application.include_router(analysis_router)
    application.include_router(interpretation_router)
    application.include_router(auth_router)
    application.include_router(action_plan_router)
    application.include_router(ai_suggestions_router)
    application.include_router(history_router)
    application.include_router(saved_profiles_router)
    application.include_router(badge_router)
    application.include_router(client_errors_router)

    def health() -> HealthResponse:
        return health_check(application_settings)

    application.get("/health", response_model=HealthResponse)(health)
    return application


app = create_app()
