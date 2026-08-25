import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.analysis import router as analysis_router
from app.api.github import router as github_router
from app.api.interpretation import router as interpretation_router
from app.config import Settings, get_settings
from app.observability import REQUEST_ID, configure_logging, emit_event, new_request_id

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: str


def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    application_settings = settings or get_settings()
    application = FastAPI(title="DevLens API", version="0.1.0")
    application.state.settings = application_settings

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
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    application.include_router(github_router)
    application.include_router(analysis_router)
    application.include_router(interpretation_router)
    application.get("/health", response_model=HealthResponse)(health_check)
    return application


app = create_app()
