"""SQLAlchemy models for sleep domain."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SleepEntry(Base):
    """Sleep entry — a single sleep session."""

    __tablename__ = "sleep_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100
    deep_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    light_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rem_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    awake_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="sleep_entries")
    stages: Mapped[list["SleepStage"]] = relationship(
        "SleepStage",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class SleepStage(Base):
    """Sleep stage data for a sleep entry."""

    __tablename__ = "sleep_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("sleep_entries.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_type: Mapped[str] = mapped_column(String(30), nullable=False)  # deep, light, rem, awake
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    entry: Mapped["SleepEntry"] = relationship(back_populates="stages")