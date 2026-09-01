"""create private action plan tasks

Revision ID: 20260901_04
Revises: 20260828_03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260901_04"
down_revision: Union[str, None] = "20260828_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "action_plan_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=True),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'todo'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("length(trim(title)) > 0", name="ck_action_plan_tasks_title_not_blank"),
        sa.CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_action_plan_tasks_status"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_plan_tasks_user_updated_at", "action_plan_tasks", ["user_id", sa.text("updated_at DESC")])


def downgrade() -> None:
    op.drop_index("ix_action_plan_tasks_user_updated_at", table_name="action_plan_tasks")
    op.drop_table("action_plan_tasks")
