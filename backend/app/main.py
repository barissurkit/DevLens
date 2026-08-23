from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.analysis import router as analysis_router
from app.api.github import router as github_router
from app.api.interpretation import router as interpretation_router
from app.config import get_settings


class HealthResponse(BaseModel):
    status: str


app = FastAPI(
    title="DevLens API",
    version="0.1.0",
)

app.state.settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(github_router)
app.include_router(analysis_router)
app.include_router(interpretation_router)


@app.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    return HealthResponse(status="ok")
