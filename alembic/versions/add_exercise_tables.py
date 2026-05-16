"""Add exercise domain tables.

Revision ID: add_exercise_tables
Revises: add_food_tables
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_exercise_tables"
down_revision: Union[str, None] = "add_food_tables"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # ── Create exercise_entries table ──
    op.create_table(
        "exercise_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("heart_rate_avg", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercise_entries_user_id"), "exercise_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_exercise_entries_start_time"), "exercise_entries", ["start_time"], unique=False)

    # ── Create exercise_entry_sets table ──
    op.create_table(
        "exercise_entry_sets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("entry_id", sa.BigInteger(), sa.ForeignKey("exercise_entries.id", ondelete="CASCADE"), nullable=False),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("distance", sa.Float(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercise_entry_sets_entry_id"), "exercise_entry_sets", ["entry_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_exercise_entry_sets_entry_id"), table_name="exercise_entry_sets")
    op.drop_table("exercise_entry_sets")

    op.drop_index(op.f("ix_exercise_entries_start_time"), table_name="exercise_entries")
    op.drop_index(op.f("ix_exercise_entries_user_id"), table_name="exercise_entries")
    op.drop_table("exercise_entries")