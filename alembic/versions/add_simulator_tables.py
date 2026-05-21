"""Add simulator tables for synthetic patient pipeline.

Revision ID: add_simulator_tables
Revises: add_event_group_id_to_health_metrics
Create Date: 2026-05-21

Tables:
- sim_runs: top-level simulation run metadata
- sim_users: per-user parameters linked to a run
- sim_hidden_truths: planted ground-truth labels (never retrieved in user-facing paths)
- sim_detector_scores: benchmark snapshots after detector evaluation
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "add_simulator_tables"
down_revision: Union[str, None] = "add_event_group_id_to_health_metrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_type = postgresql.JSONB if is_postgres else sa.JSON

    # ── sim_runs ──
    op.create_table(
        "sim_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("anchor_count", sa.Integer(), nullable=False, server_default=sa.text("12")),
        sa.Column("users_per_anchor", sa.Integer(), nullable=False, server_default=sa.text("20")),
        sa.Column("days_per_user", sa.Integer(), nullable=False, server_default=sa.text("90")),
        sa.Column("config_json", json_type, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_json", json_type, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_runs_status", "sim_runs", ["status"])
    op.create_index("ix_sim_runs_created", "sim_runs", ["created_at"])

    # ── sim_users ──
    op.create_table(
        "sim_users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sim_run_id", sa.BigInteger(), nullable=False),
        sa.Column("sim_user_key", sa.String(64), nullable=False),
        sa.Column("anchor_type", sa.String(64), nullable=False),
        sa.Column("real_user_id", sa.Integer(), nullable=True),
        sa.Column("parameter_json", json_type, nullable=True),
        sa.Column("profile_json", json_type, nullable=True),
        sa.Column("seed", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["sim_run_id"],
            ["sim_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sim_run_id", "sim_user_key", name="uq_sim_users_run_key"),
    )
    op.create_index("ix_sim_users_run", "sim_users", ["sim_run_id"])
    op.create_index("ix_sim_users_anchor", "sim_users", ["anchor_type"])

    # ── sim_hidden_truths ──
    op.create_table(
        "sim_hidden_truths",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sim_run_id", sa.BigInteger(), nullable=False),
        sa.Column("sim_user_id", sa.BigInteger(), nullable=False),
        sa.Column("pattern_type", sa.String(64), nullable=False),
        sa.Column("subtype", sa.String(64), nullable=True),
        sa.Column("source_metric_id", sa.BigInteger(), nullable=True),
        sa.Column("target_metric_id", sa.BigInteger(), nullable=True),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expected_peak_delta", sa.Float(), nullable=True),
        sa.Column("expected_time_to_peak_min", sa.Float(), nullable=True),
        sa.Column("expected_value_min", sa.Float(), nullable=True),
        sa.Column("expected_value_max", sa.Float(), nullable=True),
        sa.Column("truth_payload", json_type, nullable=True),
        sa.Column("is_detected", sa.Boolean(), nullable=True),
        sa.Column("detector_confidence", sa.Float(), nullable=True),
        sa.Column("detector_evidence", json_type, nullable=True),
        sa.Column("matched_edge_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["sim_run_id"],
            ["sim_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sim_user_id"],
            ["sim_users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_truths_run_user", "sim_hidden_truths", ["sim_run_id", "sim_user_id"])
    op.create_index("ix_sim_truths_pattern", "sim_hidden_truths", ["pattern_type"])
    op.create_index(
        "ix_sim_truths_detection",
        "sim_hidden_truths",
        ["is_detected"],
    )

    # ── sim_detector_scores ──
    op.create_table(
        "sim_detector_scores",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("sim_run_id", sa.BigInteger(), nullable=False),
        sa.Column("sim_user_id", sa.BigInteger(), nullable=True),
        sa.Column("detector_name", sa.String(128), nullable=False),
        sa.Column("detector_version", sa.String(64), nullable=False),
        sa.Column("anchor_type", sa.String(64), nullable=True),
        sa.Column("pattern_type", sa.String(64), nullable=True),
        sa.Column("metric_name", sa.String(128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("breakdown_json", json_type, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["sim_run_id"],
            ["sim_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sim_user_id"],
            ["sim_users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sim_scores_run", "sim_detector_scores", ["sim_run_id"])
    op.create_index("ix_sim_scores_detector", "sim_detector_scores", ["detector_name", "detector_version"])
    op.create_index("ix_sim_scores_metric", "sim_detector_scores", ["metric_name"])


def downgrade() -> None:
    op.drop_table("sim_detector_scores")
    op.drop_table("sim_hidden_truths")
    op.drop_table("sim_users")
    op.drop_table("sim_runs")