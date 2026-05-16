"""Add food domain tables.

Revision ID: add_food_tables
Revises: add_health_metrics_and_aggregates
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_food_tables"
down_revision: Union[str, None] = "add_health_metrics_and_aggregates"
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # ── Create foods table ──
    op.create_table(
        "foods",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("brand_name", sa.String(length=255)),
        sa.Column("serving_size", sa.Float(), default=1.0),
        sa.Column("serving_unit", sa.String(length=50), default="g"),
        sa.Column("calories", sa.Float()),
        sa.Column("protein", sa.Float()),
        sa.Column("carbs", sa.Float()),
        sa.Column("fat", sa.Float()),
        sa.Column("saturated_fat", sa.Float()),
        sa.Column("fiber", sa.Float()),
        sa.Column("sugars", sa.Float()),
        sa.Column("sodium", sa.Float()),
        sa.Column("barcode", sa.String(length=50), index=True),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_foods_user_id"), "foods", ["user_id"], unique=False)
    op.create_index(op.f("ix_foods_barcode"), "foods", ["barcode"], unique=False)

    # ── Create food_entries table ──
    op.create_table(
        "food_entries",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.BigInteger(), sa.ForeignKey("foods.id", ondelete="SET NULL"), nullable=True),
        sa.Column("quantity", sa.Float(), default=1.0, nullable=False),
        sa.Column("unit", sa.String(length=50), default="serving", nullable=False),
        sa.Column("entry_date", sa.DateTime(timezone=False), nullable=False),
        sa.Column("meal_type", sa.String(length=50), nullable=False),
        sa.Column("food_name", sa.String(length=255)),
        sa.Column("brand_name", sa.String(length=255)),
        sa.Column("serving_size", sa.Float()),
        sa.Column("serving_unit", sa.String(length=50)),
        sa.Column("calories", sa.Float()),
        sa.Column("protein", sa.Float()),
        sa.Column("carbs", sa.Float()),
        sa.Column("fat", sa.Float()),
        sa.Column("fiber", sa.Float()),
        sa.Column("sugars", sa.Float()),
        sa.Column("glycemic_index", sa.String(length=20)),
        sa.Column("source", sa.String(length=50), default="manual", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_food_entries_user_id"), "food_entries", ["user_id"], unique=False)
    op.create_index(op.f("ix_food_entries_entry_date"), "food_entries", ["entry_date"], unique=False)
    op.create_index("ix_food_entries_user_date", "food_entries", ["user_id", "entry_date"], unique=False)
    op.create_index("ix_food_entries_user_meal", "food_entries", ["user_id", "meal_type", "entry_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_food_entries_user_meal", table_name="food_entries")
    op.drop_index("ix_food_entries_user_date", table_name="food_entries")
    op.drop_index(op.f("ix_food_entries_entry_date"), table_name="food_entries")
    op.drop_index(op.f("ix_food_entries_user_id"), table_name="food_entries")
    op.drop_table("food_entries")

    op.drop_index(op.f("ix_foods_barcode"), table_name="foods")
    op.drop_index(op.f("ix_foods_user_id"), table_name="foods")
    op.drop_table("foods")