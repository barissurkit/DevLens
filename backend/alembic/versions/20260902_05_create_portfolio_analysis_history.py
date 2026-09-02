"""create private portfolio analysis history

Revision ID: 20260902_05
Revises: 20260901_04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260902_05"
down_revision: Union[str, None] = "20260901_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "portfolio_analysis_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("github_user_id", sa.BigInteger(), nullable=False),
        sa.Column("github_username", sa.String(length=39), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("analysis_version", sa.String(length=32), nullable=False),
        sa.Column("analysis_schema_version", sa.String(length=32), nullable=False),
        sa.Column("analysis_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("portfolio_score", sa.Integer(), nullable=True),
        sa.Column("category_scores", postgresql.JSONB(), nullable=False),
        sa.Column("passed_checks", postgresql.JSONB(), nullable=False),
        sa.Column("failed_checks", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "analysis_fingerprint", name="uq_portfolio_history_user_fingerprint"),
    )
    op.create_index("ix_portfolio_history_user_captured_at", "portfolio_analysis_history", ["user_id", sa.text("captured_at DESC"), sa.text("id DESC")])


def downgrade() -> None:
    op.drop_index("ix_portfolio_history_user_captured_at", table_name="portfolio_analysis_history")
    op.drop_table("portfolio_analysis_history")
