"""create saved profiles

Revision ID: 20260905_06
Revises: 20260902_05
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260905_06"
down_revision: Union[str, None] = "20260902_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "saved_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("github_username", sa.String(length=39), nullable=False),
        sa.Column("github_username_normalized", sa.String(length=39), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(github_username)) > 0", name="ck_saved_profiles_username_not_blank"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "github_username_normalized", name="uq_saved_profiles_user_username"),
    )
    op.create_index("ix_saved_profiles_user_created_at", "saved_profiles", ["user_id", sa.text("created_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_saved_profiles_user_created_at", table_name="saved_profiles")
    op.drop_table("saved_profiles")
