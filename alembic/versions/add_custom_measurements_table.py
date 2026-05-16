"""Add custom measurements table.

Revision ID: add_custom_measurements_table
Revises: add_exercise_tables
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_custom_measurements_table"
down_revision: Union[str, None] = "add_exercise_tables"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # ── Create custom_measurements table ──
    op.create_table(
        "custom_measurements",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("metric_name", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_custom_measurements_user_id"), "custom_measurements", ["user_id"], unique=False)
    op.create_index(op.f("ix_custom_measurements_measured_at"), "custom_measurements", ["measured_at"], unique=False)
    op.create_index("ix_custom_measurements_user_time", "custom_measurements", ["user_id", "measured_at"], unique=False)
    op.create_index("ix_custom_measurements_user_metric", "custom_measurements", ["user_id", "metric_name", "measured_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_custom_measurements_user_metric", table_name="custom_measurements")
    op.drop_index("ix_custom_measurements_user_time", table_name="custom_measurements")
    op.drop_index(op.f("ix_custom_measurements_measured_at"), table_name="custom_measurements")
    op.drop_index(op.f("ix_custom_measurements_user_id"), table_name="custom_measurements")
    op.drop_table("custom_measurements")