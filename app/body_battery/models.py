"""SQLAlchemy models for body battery domain."""

from datetime import datetime
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BodyBatteryEntry(Base):
    """Body battery entry — tracks Garmin-style recovery/energy reserve."""

    __tablename__ = "body_battery_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    change: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    charged: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    drained: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="body_battery_entries")

    __table_args__ = (
        Index("ix_body_battery_user_measured", "user_id", "measured_at"),
    )
