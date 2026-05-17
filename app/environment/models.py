"""SQLAlchemy models for environment domain."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class EnvironmentEntry(Base):
    """Environment entry — environmental conditions measurement."""

    __tablename__ = "environment_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Celsius
    humidity_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0-100%
    altitude_m: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # meters above sea level
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="environment_entries")