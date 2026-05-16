"""Add fasting, mood, and water domain tables.

Revision ID: add_fasting_mood_water_tables
Revises: add_custom_measurements_table
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_fasting_mood_water_tables"
down_revision: Union[str, None] = "add_custom_measurements_table"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # ── Create fasting_entries table ──
    op.create_table(
        "fasting_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fasting_entries_user_id"), "fasting_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_fasting_entries_start_time"), "fasting_entries", ["start_time"], unique=False)

    # ── Create mood_entries table ──
    op.create_table(
        "mood_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_mood_entries_user_id"), "mood_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_mood_entries_logged_at"), "mood_entries", ["logged_at"], unique=False)

    # ── Create water_entries table ──
    op.create_table(
        "water_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount_ml", sa.Integer(), nullable=False),
        sa.Column("logged_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_water_entries_user_id"), "water_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_water_entries_logged_at"), "water_entries", ["logged_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_water_entries_logged_at"), table_name="water_entries")
    op.drop_index(op.f("ix_water_entries_user_id"), table_name="water_entries")
    op.drop_table("water_entries")

    op.drop_index(op.f("ix_mood_entries_logged_at"), table_name="mood_entries")
    op.drop_index(op.f("ix_mood_entries_user_id"), table_name="mood_entries")
    op.drop_table("mood_entries")

    op.drop_index(op.f("ix_fasting_entries_start_time"), table_name="fasting_entries")
    op.drop_index(op.f("ix_fasting_entries_user_id"), table_name="fasting_entries")
    op.drop_table("fasting_entries")