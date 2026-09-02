from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_required_authenticated_user
from app.db.database import get_session
from app.db.models import User, PortfolioAnalysisHistory
from app.db.repositories.portfolio_history import list_history
from app.schemas.history import HistoryDelta, HistoryRecord, HistoryResponse

router = APIRouter(prefix="/api/v1/workspace", tags=["Workspace History"])


async def require_history_user(request: Request, response: Response, session: AsyncSession = Depends(get_session)) -> User:
    return await get_required_authenticated_user(request, response, session)


def compare_history(latest: PortfolioAnalysisHistory, previous: PortfolioAnalysisHistory) -> HistoryDelta:
    if latest.analysis_version != previous.analysis_version or latest.analysis_schema_version != previous.analysis_schema_version:
        return HistoryDelta(portfolio_score=None, category_scores=[], newly_passing_checks=[], newly_failing_checks=[], comparable=False, note="Farklı analiz sürümleri doğrudan karşılaştırılamaz.")
    latest_categories = {item["key"]: item for item in latest.category_scores}
    previous_categories = {item["key"]: item for item in previous.category_scores}
    deltas = [
        {"key": key, "label": str(item["label"]), "delta": int(item["score"]) - int(previous_categories[key]["score"])}
        for key, item in latest_categories.items() if key in previous_categories
    ]
    return HistoryDelta(
        portfolio_score=(latest.portfolio_score - previous.portfolio_score) if latest.portfolio_score is not None and previous.portfolio_score is not None else None,
        category_scores=deltas,
        newly_passing_checks=sorted(set(latest.passed_checks) - set(previous.passed_checks)),
        newly_failing_checks=sorted(set(latest.failed_checks) - set(previous.failed_checks)),
        comparable=True,
    )


@router.get("/analysis-history", response_model=HistoryResponse)
async def get_analysis_history(user: User = Depends(require_history_user), session: AsyncSession = Depends(get_session)) -> HistoryResponse:
    rows = await list_history(session, user.id)
    records = [HistoryRecord.model_validate(row) for row in rows]
    latest = records[0] if records else None
    previous = records[1] if len(records) > 1 else None
    comparison = compare_history(rows[0], rows[1]) if len(rows) > 1 else None
    return HistoryResponse(latest=latest, previous=previous, comparison=comparison, history=records)
