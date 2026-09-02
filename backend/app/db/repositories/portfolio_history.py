import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.constants import ANALYSIS_SNAPSHOT_SCHEMA_VERSION
from app.db.models import PortfolioAnalysisHistory, User
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.services.portfolio_scoring import is_portfolio_rule_passing


@dataclass(frozen=True)
class HistoryProjection:
    portfolio_score: int | None
    category_scores: list[dict[str, object]]
    passed_checks: list[str]
    failed_checks: list[str]
    analysis_version: str
    analysis_schema_version: str
    fingerprint: str


def project_analysis(analysis: GitHubPortfolioAnalysis) -> HistoryProjection:
    categories = [
        {"key": dimension.key, "label": dimension.label, "score": dimension.score}
        for dimension in analysis.score.dimensions
    ]
    # Portfolio score rules expose coverage counts rather than the repository
    # score rule's boolean ``passed`` field.
    passed = sorted(
        rule.key
        for dimension in analysis.score.dimensions
        for rule in dimension.rules
        if is_portfolio_rule_passing(
            detected_repository_count=rule.detected_repository_count,
            analyzed_repository_count=rule.analyzed_repository_count,
        )
    )
    failed = sorted(
        rule.key
        for dimension in analysis.score.dimensions
        for rule in dimension.rules
        if not is_portfolio_rule_passing(
            detected_repository_count=rule.detected_repository_count,
            analyzed_repository_count=rule.analyzed_repository_count,
        )
    )
    payload = {
        "portfolio_score": analysis.score.overall_score,
        "category_scores": categories,
        "passed_checks": passed,
        "failed_checks": failed,
        "analysis_version": analysis.score.version,
        "analysis_schema_version": ANALYSIS_SNAPSHOT_SCHEMA_VERSION,
    }
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return HistoryProjection(**payload, fingerprint=fingerprint)


async def capture_history(session: AsyncSession, user: User, analysis: GitHubPortfolioAnalysis) -> PortfolioAnalysisHistory:
    projection = project_analysis(analysis)
    existing = await session.scalar(select(PortfolioAnalysisHistory).where(
        PortfolioAnalysisHistory.user_id == user.id,
        PortfolioAnalysisHistory.analysis_fingerprint == projection.fingerprint,
    ))
    if existing is not None:
        return existing
    row = PortfolioAnalysisHistory(
        user_id=user.id,
        github_user_id=analysis.user.github_user_id,
        github_username=analysis.user.username,
        captured_at=datetime.now(timezone.utc),
        analysis_version=projection.analysis_version,
        analysis_schema_version=projection.analysis_schema_version,
        analysis_fingerprint=projection.fingerprint,
        portfolio_score=projection.portfolio_score,
        category_scores=projection.category_scores,
        passed_checks=projection.passed_checks,
        failed_checks=projection.failed_checks,
    )
    session.add(row)
    await session.flush()
    return row


async def list_history(session: AsyncSession, user_id: UUID, limit: int = 20) -> list[PortfolioAnalysisHistory]:
    result = await session.execute(select(PortfolioAnalysisHistory).where(
        PortfolioAnalysisHistory.user_id == user_id
    ).order_by(desc(PortfolioAnalysisHistory.captured_at), desc(PortfolioAnalysisHistory.id)).limit(limit))
    return list(result.scalars())
