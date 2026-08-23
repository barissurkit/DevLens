from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AnalysisSnapshot(Base):
    __tablename__ = "analysis_snapshots"
    __table_args__ = (
        Index(
            "ix_analysis_snapshots_username_created_at",
            "github_username_normalized",
            text("created_at DESC"),
        ),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    github_username: Mapped[str] = mapped_column(String(39), nullable=False)
    github_username_normalized: Mapped[str] = mapped_column(String(39), nullable=False)
    analysis_schema_version: Mapped[str] = mapped_column(String(32), nullable=False)
    analysis_engine_version: Mapped[str] = mapped_column(String(32), nullable=False)
    interpretation_schema_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    analysis_payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    interpretation_payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    analysis_generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
