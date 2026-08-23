import os
import asyncio

import httpx
import pytest
from sqlalchemy import func, select

from app.api.github import get_gemini_client, get_github_client
from app.db.database import dispose_engine, get_engine, get_session_factory
from app.db.models import AnalysisSnapshot
from app.main import app
from app.schemas.interpretation import (
    InterpretationExplanation,
    NextProjectRecommendation,
    PortfolioInterpretation,
)

from test_analysis_e2e import portfolio_fixture, use_fake_github


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="requires disposable PostgreSQL")
def test_public_analysis_and_interpretation_persist_one_snapshot_each() -> None:
    asyncio.run(_run_public_snapshot_flow())


async def _run_public_snapshot_flow() -> None:
    repositories, files = portfolio_fixture()
    use_fake_github(repositories, files_by_repository=files)

    class FakeGemini:
        async def interpret(self, context):
            return PortfolioInterpretation(
                summary="Persisted interpretation.",
                strength_explanations=[
                    InterpretationExplanation(
                        signal_key=signal.key, explanation="Grounded strength."
                    )
                    for signal in context.strength_signals
                ],
                improvement_explanations=[
                    InterpretationExplanation(
                        signal_key=signal.key, explanation="Grounded improvement."
                    )
                    for signal in context.improvement_signals
                ],
                next_project_recommendation=(
                    NextProjectRecommendation(
                        title="Improve portfolio depth",
                        goal="Add a focused project.",
                        rationale="Addresses deterministic improvement signals.",
                        focus_signal_keys=[context.improvement_signals[0].key],
                        suggested_deliverables=["API", "Tests", "Docs"],
                    )
                    if context.improvement_signals
                    else None
                ),
            )

    async def gemini_override() -> FakeGemini:
        return FakeGemini()

    app.dependency_overrides[get_gemini_client] = gemini_override
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            analysis_response = await client.post(
                "/api/v1/analysis", json={"username": "synthetic-user"}
            )
            interpretation_response = await client.post(
                "/api/v1/interpretation", json={"username": "synthetic-user"}
            )

        assert analysis_response.status_code == 200
        assert interpretation_response.status_code == 200
        assert interpretation_response.json()["interpretation"]["status"] == "available"

        session_factory = get_session_factory()
        async with session_factory() as session:
            rows = (
                await session.execute(
                    select(AnalysisSnapshot)
                    .where(AnalysisSnapshot.github_username_normalized == "synthetic-user")
                    .order_by(AnalysisSnapshot.created_at, AnalysisSnapshot.id)
                )
            ).scalars().all()

        assert len(rows) == 2
        assert rows[0].interpretation_payload is None
        assert rows[0].analysis_payload == analysis_response.json()
        assert rows[1].analysis_payload == interpretation_response.json()["analysis"]
        assert rows[1].interpretation_payload == interpretation_response.json()["interpretation"]
    finally:
        app.dependency_overrides.clear()
        await dispose_engine(get_engine())
        get_engine.cache_clear()
