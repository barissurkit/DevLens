"""create analysis snapshots

Revision ID: 20260823_01
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260823_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("github_username", sa.String(length=39), nullable=False),
        sa.Column("github_username_normalized", sa.String(length=39), nullable=False),
        sa.Column("analysis_schema_version", sa.String(length=32), nullable=False),
        sa.Column("interpretation_schema_version", sa.String(length=32), nullable=True),
        sa.Column("analysis_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("interpretation_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_analysis_snapshots_username_created_at",
        "analysis_snapshots",
        ["github_username_normalized", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_snapshots_username_created_at", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
