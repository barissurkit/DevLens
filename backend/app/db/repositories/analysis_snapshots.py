from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from pydantic import TypeAdapter, ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.constants import ANALYSIS_SNAPSHOT_SCHEMA_VERSION, INTERPRETATION_SNAPSHOT_SCHEMA_VERSION
from app.db.models import AnalysisSnapshot
from app.db.normalization import normalize_github_username
from app.schemas.analysis import GitHubPortfolioAnalysis
from app.schemas.interpretation import PublicPortfolioInterpretationResult


class SnapshotPayloadValidationError(ValueError):
    """Raised when a persisted snapshot no longer matches its public contract."""


_interpretation_adapter = TypeAdapter(PublicPortfolioInterpretationResult)


@dataclass(frozen=True)
class AnalysisSnapshotRecord:
    id: UUID
    github_username: str
    github_username_normalized: str
    analysis_schema_version: str
    interpretation_schema_version: str | None
    analysis: GitHubPortfolioAnalysis
    interpretation: PublicPortfolioInterpretationResult | None
    created_at: datetime


class AnalysisSnapshotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        github_username: str,
        analysis: GitHubPortfolioAnalysis,
        interpretation: PublicPortfolioInterpretationResult | None = None,
    ) -> AnalysisSnapshotRecord:
        normalized = normalize_github_username(github_username)
        row = AnalysisSnapshot(
            github_username=github_username.strip(),
            github_username_normalized=normalized,
            analysis_schema_version=ANALYSIS_SNAPSHOT_SCHEMA_VERSION,
            interpretation_schema_version=(
                INTERPRETATION_SNAPSHOT_SCHEMA_VERSION if interpretation is not None else None
            ),
            analysis_payload=analysis.model_dump(mode="json"),
            interpretation_payload=(
                _interpretation_adapter.dump_python(interpretation, mode="json")
                if interpretation is not None
                else None
            ),
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def get_latest_by_username(self, username: str) -> AnalysisSnapshotRecord | None:
        normalized = normalize_github_username(username)
        result = await self._session.execute(
            select(AnalysisSnapshot)
            .where(AnalysisSnapshot.github_username_normalized == normalized)
            .order_by(desc(AnalysisSnapshot.created_at), desc(AnalysisSnapshot.id))
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return self._to_record(row) if row is not None else None

    @staticmethod
    def _to_record(row: AnalysisSnapshot) -> AnalysisSnapshotRecord:
        try:
            analysis = GitHubPortfolioAnalysis.model_validate(row.analysis_payload)
            interpretation = (
                _interpretation_adapter.validate_python(row.interpretation_payload)
                if row.interpretation_payload is not None
                else None
            )
        except ValidationError as exc:
            raise SnapshotPayloadValidationError(
                "Persisted snapshot payload failed schema validation."
            ) from exc
        if row.created_at.tzinfo is None:
            raise SnapshotPayloadValidationError("Snapshot created_at must be timezone-aware.")
        return AnalysisSnapshotRecord(
            id=row.id,
            github_username=row.github_username,
            github_username_normalized=row.github_username_normalized,
            analysis_schema_version=row.analysis_schema_version,
            interpretation_schema_version=row.interpretation_schema_version,
            analysis=analysis,
            interpretation=interpretation,
            created_at=row.created_at.astimezone(timezone.utc),
        )
