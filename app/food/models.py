"""SQLAlchemy models for food tracking domain.

Ported from SparkyFitness db_schema_backup.sql food-related tables.
"""

from datetime import datetime
from typing import Any, Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Food(Base):
    """Food master — individual food items with nutrition per serving."""

    __tablename__ = "foods"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    brand_name: Mapped[Optional[str]] = mapped_column(String(255))
    serving_size: Mapped[Optional[float]] = mapped_column(Float, default=1)
    serving_unit: Mapped[Optional[str]] = mapped_column(String(50), default="g")
    calories: Mapped[Optional[float]] = mapped_column(Float)
    protein: Mapped[Optional[float]] = mapped_column(Float)
    carbs: Mapped[Optional[float]] = mapped_column(Float)
    fat: Mapped[Optional[float]] = mapped_column(Float)
    saturated_fat: Mapped[Optional[float]] = mapped_column(Float)
    fiber: Mapped[Optional[float]] = mapped_column(Float)
    sugars: Mapped[Optional[float]] = mapped_column(Float)
    sodium: Mapped[Optional[float]] = mapped_column(Float)
    barcode: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="foods")
    food_entries: Mapped[List["FoodEntry"]] = relationship(back_populates="food")


class FoodEntry(Base):
    """Food entry — a single logged consumption of a food (or a meal)."""

    __tablename__ = "food_entries"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False, index=True)
    food_id: Mapped[Optional[int]] = mapped_column(ForeignKey("foods.id", ondelete="SET NULL"))
    quantity: Mapped[float] = mapped_column(Float, default=1, nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="serving", nullable=False)
    entry_date: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    meal_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="breakfast, lunch, dinner, snack")
    food_name: Mapped[Optional[str]] = mapped_column(String(255))
    brand_name: Mapped[Optional[str]] = mapped_column(String(255))
    serving_size: Mapped[Optional[float]] = mapped_column(Float)
    serving_unit: Mapped[Optional[str]] = mapped_column(String(50))
    calories: Mapped[Optional[float]] = mapped_column(Float)
    protein: Mapped[Optional[float]] = mapped_column(Float)
    carbs: Mapped[Optional[float]] = mapped_column(Float)
    fat: Mapped[Optional[float]] = mapped_column(Float)
    fiber: Mapped[Optional[float]] = mapped_column(Float)
    sugars: Mapped[Optional[float]] = mapped_column(Float)
    glycemic_index: Mapped[Optional[str]] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(50), default="manual", nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column("metadata", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user: Mapped["User"] = relationship(back_populates="food_entries")
    food: Mapped[Optional["Food"]] = relationship(back_populates="food_entries")

    __table_args__ = (
        Index("ix_food_entries_user_date", "user_id", "entry_date"),
        Index("ix_food_entries_user_meal", "user_id", "meal_type", "entry_date"),
    )
