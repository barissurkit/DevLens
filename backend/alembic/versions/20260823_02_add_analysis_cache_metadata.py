"""add analysis cache metadata

Revision ID: 20260823_02
Revises: 20260823_01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260823_02"
down_revision: Union[str, None] = "20260823_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analysis_snapshots",
        sa.Column("analysis_generated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "analysis_snapshots",
        sa.Column("analysis_engine_version", sa.String(length=32), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE analysis_snapshots "
            "SET analysis_generated_at = created_at, analysis_engine_version = 'v1'"
        )
    )
    op.alter_column("analysis_snapshots", "analysis_generated_at", nullable=False)
    op.alter_column("analysis_snapshots", "analysis_engine_version", nullable=False)
    op.create_index(
        "ix_analysis_snapshots_analysis_cache",
        "analysis_snapshots",
        [
            "github_username_normalized",
            "analysis_schema_version",
            "analysis_engine_version",
            sa.text("analysis_generated_at DESC"),
        ],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_snapshots_analysis_cache", table_name="analysis_snapshots")
    op.drop_column("analysis_snapshots", "analysis_engine_version")
    op.drop_column("analysis_snapshots", "analysis_generated_at")
