"""SQLAlchemy models for body composition domain."""

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BodyCompositionEntry(Base):
    """Body composition entry — tracks weight, body fat %, BMI, lean mass, waist."""

    __tablename__ = "body_composition_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    weight_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    body_fat_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bmi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lean_mass_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="body_composition_entries")

    __table_args__ = (
        Index("ix_body_comp_user_measured", "user_id", "measured_at"),
    )
