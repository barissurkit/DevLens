from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.analysis import router as analysis_router
from app.api.github import router as github_router
from app.api.interpretation import router as interpretation_router
from app.config import Settings, get_settings


class HealthResponse(BaseModel):
    status: str


def health_check() -> HealthResponse:
    return HealthResponse(status="ok")


def create_app(settings: Settings | None = None) -> FastAPI:
    application_settings = settings or get_settings()
    application = FastAPI(title="DevLens API", version="0.1.0")
    application.state.settings = application_settings
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
