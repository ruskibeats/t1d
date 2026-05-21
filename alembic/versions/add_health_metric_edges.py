"""add health metric graph edges

Revision ID: add_health_metric_edges
Revises: 7d5b6f1aca4b
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "add_health_metric_edges"
down_revision: Union[str, None] = "7d5b6f1aca4b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EDGE_TYPES = (
    "meal_to_glucose_spike",
    "meal_to_delayed_spike",
    "exercise_to_glucose_drop",
    "exercise_to_glucose_rise",
    "insulin_to_glucose_change",
    "sleep_to_next_day_glucose",
    "stress_to_glucose_rise",
    "heart_rate_to_low_glucose",
    "hydration_to_glucose_stability",
    "correlates_with",
    "precedes",
    "same_event_as",
)


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        # Create the ENUM type if it doesn't exist (using raw SQL for IF NOT EXISTS)
        op.execute("""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'graph_edge_type') THEN
        CREATE TYPE graph_edge_type AS ENUM (
            'meal_to_glucose_spike', 'meal_to_delayed_spike',
            'exercise_to_glucose_drop', 'exercise_to_glucose_rise',
            'insulin_to_glucose_change', 'sleep_to_next_day_glucose',
            'stress_to_glucose_rise', 'heart_rate_to_low_glucose',
            'hydration_to_glucose_stability', 'correlates_with',
            'precedes', 'same_event_as'
        );
    END IF;
END
$$;
""")
        # create_type=False so the table creation below doesn't try to
        # CREATE TYPE a second time (the type already exists at this point)
        edge_type = postgresql.ENUM(*EDGE_TYPES, name="graph_edge_type", create_type=False)
    else:
        edge_type = sa.String(length=64)

    op.create_table(
        "health_metric_edges",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("source_metric_id", sa.BigInteger(), nullable=False),
        sa.Column("target_metric_id", sa.BigInteger(), nullable=False),
        sa.Column("edge_type", edge_type, nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("time_delay_seconds", sa.Integer(), nullable=True),
        sa.Column("algorithm", sa.String(length=100), nullable=False),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_health_edges_confidence_range"),
        sa.CheckConstraint("source_metric_id <> target_metric_id", name="ck_health_edges_not_self"),
        sa.ForeignKeyConstraint(["source_metric_id"], ["health_metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_metric_id"], ["health_metrics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["tbl_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_metric_id", "target_metric_id", "edge_type", name="uq_health_edges_source_target_type"),
    )
    op.create_index("ix_health_edges_user_source", "health_metric_edges", ["user_id", "source_metric_id"])
    op.create_index("ix_health_edges_user_target", "health_metric_edges", ["user_id", "target_metric_id"])
    op.create_index("ix_health_edges_user_type", "health_metric_edges", ["user_id", "edge_type"])
    op.create_index("ix_health_edges_user_type_conf", "health_metric_edges", ["user_id", "edge_type", "confidence"])


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    op.drop_index("ix_health_edges_user_type_conf", table_name="health_metric_edges")
    op.drop_index("ix_health_edges_user_type", table_name="health_metric_edges")
    op.drop_index("ix_health_edges_user_target", table_name="health_metric_edges")
    op.drop_index("ix_health_edges_user_source", table_name="health_metric_edges")
    op.drop_table("health_metric_edges")

    if is_postgres:
        edge_type = postgresql.ENUM(*EDGE_TYPES, name="graph_edge_type")
        edge_type.drop(bind, checkfirst=True)
