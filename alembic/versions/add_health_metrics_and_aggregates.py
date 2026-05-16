"""Add health_metrics and health_daily_aggregates tables.

Revision ID: add_health_metrics_and_aggregates
Revises:
Create Date: 2026-05-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "add_health_metrics_and_aggregates"
down_revision: Union[str, None] = None
branch_labels: Union[Sequence[str], None] = None
depends_on: Union[Sequence[str], None] = None


def upgrade() -> None:
    # ── Create PostgreSQL enum type ──
    metric_type_enum = postgresql.ENUM(
        "blood_glucose",
        "insulin",
        "insulin_basal",
        "insulin_bolus",
        "insulin_correction",
        "cgm_trend",
        "estimated_a1c",
        "carbs",
        "protein",
        "fat",
        "fiber",
        "calories",
        "glycemic_index",
        "glycemic_load",
        "water",
        "caffeine",
        "exercise_minutes",
        "exercise_calories",
        "steps",
        "distance_km",
        "floors_climbed",
        "heart_rate",
        "resting_heart_rate",
        "heart_rate_variability",
        "spo2",
        "respiratory_rate",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "sleep_hours",
        "sleep_deep",
        "sleep_rem",
        "sleep_light",
        "sleep_awake",
        "sleep_score",
        "sleep_latency",
        "body_battery_change",
        "avg_sleep_stress",
        "weight",
        "body_fat_percent",
        "bmi",
        "waist_circumference",
        "lean_mass",
        "fasting_duration",
        "mood_score",
        "stress_level",
        "energy_level",
        "temperature",
        "humidity",
        "altitude",
        "custom",
        name="metric_type",
        create_type=True,
    )
    metric_type_enum.create(op.get_bind(), checkfirst=True)

    # ── health_metrics table ──
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", metric_type_enum, nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("unit", sa.String(length=50), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("provider_id", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_health_metrics_measured_at"), "health_metrics", ["measured_at"], unique=False)
    op.create_index(op.f("ix_health_metrics_type"), "health_metrics", ["type"], unique=False)
    op.create_index("ix_health_metrics_user_time", "health_metrics", ["user_id", "measured_at"], unique=False)
    op.create_index("ix_health_metrics_user_type_time", "health_metrics", ["user_id", "type", "measured_at"], unique=False)
    op.create_index("ix_health_metrics_dedup", "health_metrics", ["user_id", "type", "source", "provider_id"], unique=True, postgresql_where=sa.text("provider_id IS NOT NULL"))

    # ── health_daily_aggregates table ──
    op.create_table(
        "health_daily_aggregates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", metric_type_enum, nullable=False),
        sa.Column("local_date", sa.DateTime(timezone=False), nullable=False),
        sa.Column("value_sum", sa.Float(), nullable=True),
        sa.Column("value_avg", sa.Float(), nullable=True),
        sa.Column("value_min", sa.Float(), nullable=True),
        sa.Column("value_max", sa.Float(), nullable=True),
        sa.Column("value_last", sa.Float(), nullable=True),
        sa.Column("value_count", sa.Integer(), nullable=False, default=0),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("source_primary", sa.String(length=50), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("aggregation_version", sa.Integer(), nullable=False, default=1),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "type", "local_date", name="uq_aggregates_user_type_date"),
    )
    op.create_index(op.f("ix_health_daily_aggregates_local_date"), "health_daily_aggregates", ["local_date"], unique=False)
    op.create_index(op.f("ix_health_daily_aggregates_type"), "health_daily_aggregates", ["type"], unique=False)
    op.create_index("ix_aggregates_user_date", "health_daily_aggregates", ["user_id", "local_date"], unique=False)
    op.create_index("ix_aggregates_user_type_date", "health_daily_aggregates", ["user_id", "type", "local_date"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_aggregates_user_type_date", table_name="health_daily_aggregates")
    op.drop_index("ix_aggregates_user_date", table_name="health_daily_aggregates")
    op.drop_index(op.f("ix_health_daily_aggregates_type"), table_name="health_daily_aggregates")
    op.drop_index(op.f("ix_health_daily_aggregates_local_date"), table_name="health_daily_aggregates")
    op.drop_table("health_daily_aggregates")

    op.drop_index("ix_health_metrics_dedup", table_name="health_metrics")
    op.drop_index("ix_health_metrics_user_type_time", table_name="health_metrics")
    op.drop_index("ix_health_metrics_user_time", table_name="health_metrics")
    op.drop_index(op.f("ix_health_metrics_type"), table_name="health_metrics")
    op.drop_index(op.f("ix_health_metrics_measured_at"), table_name="health_metrics")
    op.drop_table("health_metrics")

    # Drop enum type
    metric_type_enum = postgresql.ENUM(name="metric_type", create_type=False)
    metric_type_enum.drop(op.get_bind(), checkfirst=True)
