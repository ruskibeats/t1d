"""SQLAlchemy models for feature flag persistence.

Supports global flags (feature_flags) and per-user overrides (user_feature_overrides).
Both tables are optional — the FeatureFlagService falls back to env vars and defaults
if these tables don't exist.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FeatureFlagModel(Base):
    """Global feature flag — applies to all users by default."""

    __tablename__ = "tbl_feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flag_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    flag_value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<FeatureFlagModel(name={self.flag_name}, value={self.flag_value})>"


class UserFeatureOverrideModel(Base):
    """Per-user feature flag override — overrides the global flag for a specific user."""

    __tablename__ = "tbl_user_feature_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    flag_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    flag_value: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", "flag_name", name="uq_user_feature_flag"),
    )

    def __repr__(self) -> str:
        return (
            f"<UserFeatureOverrideModel(user_id={self.user_id}, "
            f"flag={self.flag_name}, value={self.flag_value})>"
        )