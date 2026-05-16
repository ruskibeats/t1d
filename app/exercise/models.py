"""SQLAlchemy models for exercise domain."""

from datetime import datetime
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExerciseEntry(Base):
    """Exercise entry — a single logged exercise session."""

    __tablename__ = "exercise_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "running", "cycling", "weightlifting"
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    calories: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heart_rate_avg: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="exercise_entries")
    sets: Mapped[List["ExerciseEntrySet"]] = relationship(back_populates="entry", cascade="all, delete-orphan")


class ExerciseEntrySet(Base):
    """Exercise entry set — a single set within an exercise entry (e.g., 3 sets of 10 reps)."""

    __tablename__ = "exercise_entry_sets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("exercise_entries.id", ondelete="CASCADE"), nullable=False)
    set_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in kg or lbs
    distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # in km or miles
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # for timed sets

    entry: Mapped["ExerciseEntry"] = relationship(back_populates="sets")

    __table_args__ = (
        Index("ix_exercise_entry_sets_entry_id", "entry_id"),
    )