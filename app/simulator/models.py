"""SQLAlchemy ORM models for the simulator pipeline.

These tables store simulation run metadata, synthetic patient parameters,
planted ground-truth labels, and detector evaluation scores.

IMPORTANT: sim_hidden_truths must NEVER be accessible through user-facing
RAG context, graph queries, or chat endpoints.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SimRun(Base):
    """Top-level simulation run."""

    __tablename__ = "sim_runs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    anchor_count: Mapped[int] = mapped_column(Integer, nullable=False, default=12)
    users_per_anchor: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    days_per_user: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    config_json: Mapped[Optional[dict[str, Any]]] = mapped_column("config_json", JSONB, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[Optional[dict[str, Any]]] = mapped_column("summary_json", JSONB, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sim_users: Mapped[list["SimUser"]] = relationship(
        "SimUser",
        back_populates="sim_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    hidden_truths: Mapped[list["SimHiddenTruth"]] = relationship(
        "SimHiddenTruth",
        back_populates="sim_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    detector_scores: Mapped[list["SimDetectorScore"]] = relationship(
        "SimDetectorScore",
        back_populates="sim_run",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_sim_runs_status", "status"),
        Index("ix_sim_runs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<SimRun(id={self.id}, name='{self.name}', status='{self.status}')>"


class SimUser(Base):
    """A single synthetic patient within a simulation run."""

    __tablename__ = "sim_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sim_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sim_runs.id", ondelete="CASCADE"), nullable=False
    )
    sim_user_key: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_type: Mapped[str] = mapped_column(String(64), nullable=False)
    real_user_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    parameter_json: Mapped[Optional[dict[str, Any]]] = mapped_column("parameter_json", JSONB, nullable=True)
    profile_json: Mapped[Optional[dict[str, Any]]] = mapped_column("profile_json", JSONB, nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sim_run: Mapped["SimRun"] = relationship("SimRun", back_populates="sim_users")
    hidden_truths: Mapped[list["SimHiddenTruth"]] = relationship(
        "SimHiddenTruth",
        back_populates="sim_user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    detector_scores: Mapped[list["SimDetectorScore"]] = relationship(
        "SimDetectorScore",
        back_populates="sim_user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("sim_run_id", "sim_user_key", name="uq_sim_users_run_key"),
        Index("ix_sim_users_run", "sim_run_id"),
        Index("ix_sim_users_anchor", "anchor_type"),
    )

    def __repr__(self) -> str:
        return f"<SimUser(id={self.id}, run={self.sim_run_id}, anchor='{self.anchor_type}', key='{self.sim_user_key}')>"


class SimHiddenTruth(Base):
    """Planted ground-truth label for a simulation.

    Every planted pattern (post-meal spike, overnight low, exercise effect, etc.)
    is recorded here. These records are the evaluation reference — they must
    never appear in user-facing RAG context, graph queries, or chat endpoints.

    After the detector run, is_detected, detector_confidence, and
    detector_evidence are populated by the evaluator.
    """

    __tablename__ = "sim_hidden_truths"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sim_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sim_runs.id", ondelete="CASCADE"), nullable=False
    )
    sim_user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sim_users.id", ondelete="CASCADE"), nullable=False
    )
    pattern_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subtype: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # References to the planted health_metrics nodes (may be None for windowed truths)
    source_metric_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    target_metric_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    # Time window for the expected pattern
    window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Expected pattern characteristics
    expected_peak_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_time_to_peak_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_value_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_value_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    truth_payload: Mapped[Optional[dict[str, Any]]] = mapped_column("truth_payload", JSONB, nullable=True)

    # Populated by the evaluator after detector run
    is_detected: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    detector_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    detector_evidence: Mapped[Optional[dict[str, Any]]] = mapped_column("detector_evidence", JSONB, nullable=True)
    matched_edge_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sim_run: Mapped["SimRun"] = relationship("SimRun", back_populates="hidden_truths")
    sim_user: Mapped["SimUser"] = relationship("SimUser", back_populates="hidden_truths")

    __table_args__ = (
        Index("ix_sim_truths_run_user", "sim_run_id", "sim_user_id"),
        Index("ix_sim_truths_pattern", "pattern_type"),
        Index("ix_sim_truths_detection", "is_detected"),
    )

    def __repr__(self) -> str:
        return (
            f"<SimHiddenTruth(id={self.id}, user={self.sim_user_id}, "
            f"pattern='{self.pattern_type}', detected={self.is_detected})>"
        )


class SimDetectorScore(Base):
    """Benchmark snapshot for a detector evaluation.

    One row per (run, user, detector, metric) tuple. Aggregated scores
    are computed by the evaluator and stored here for reporting.
    """

    __tablename__ = "sim_detector_scores"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    sim_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sim_runs.id", ondelete="CASCADE"), nullable=False
    )
    sim_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sim_users.id", ondelete="SET NULL"), nullable=True
    )
    detector_name: Mapped[str] = mapped_column(String(128), nullable=False)
    detector_version: Mapped[str] = mapped_column(String(64), nullable=False)
    anchor_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    pattern_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown_json: Mapped[Optional[dict[str, Any]]] = mapped_column("breakdown_json", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    sim_run: Mapped["SimRun"] = relationship("SimRun", back_populates="detector_scores")
    sim_user: Mapped["SimUser"] = relationship("SimUser", back_populates="detector_scores")

    __table_args__ = (
        Index("ix_sim_scores_run", "sim_run_id"),
        Index("ix_sim_scores_detector", "detector_name", "detector_version"),
        Index("ix_sim_scores_metric", "metric_name"),
    )

    def __repr__(self) -> str:
        return (
            f"<SimDetectorScore(id={self.id}, detector='{self.detector_name}', "
            f"metric='{self.metric_name}'={self.metric_value})>"
        )
