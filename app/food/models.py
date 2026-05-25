"""SQLAlchemy models for food tracking domain.

Ported from SparkyFitness db_schema_backup.sql food-related tables.
"""

from datetime import datetime
from typing import Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.db.models import User

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

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
    glycemic_load: Mapped[Optional[float]] = mapped_column(Float)
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


class OpenFoodFactsProduct(Base):
    """Compact Open Food Facts lookup table for barcode and nutrition search.

    This table stores a T1D-focused projection of the upstream JSONL export.
    The raw export remains on disk and should be streamed, not loaded with
    pandas or expanded into application memory.
    """

    __tablename__ = "openfoodfacts_products"

    code: Mapped[str] = mapped_column(String(64), primary_key=True)
    product_name: Mapped[Optional[str]] = mapped_column(Text)
    brands: Mapped[Optional[str]] = mapped_column(Text)
    categories: Mapped[Optional[str]] = mapped_column(Text)
    categories_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text).with_variant(JSON, "sqlite"))
    countries_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text).with_variant(JSON, "sqlite"))
    serving_size: Mapped[Optional[str]] = mapped_column(Text)
    serving_quantity: Mapped[Optional[float]] = mapped_column(Float)
    product_quantity: Mapped[Optional[float]] = mapped_column(Float)
    product_quantity_unit: Mapped[Optional[str]] = mapped_column(Text)
    nutrition_data_per: Mapped[Optional[str]] = mapped_column(Text)
    carbs_100g: Mapped[Optional[float]] = mapped_column(Float)
    sugars_100g: Mapped[Optional[float]] = mapped_column(Float)
    fiber_100g: Mapped[Optional[float]] = mapped_column(Float)
    proteins_100g: Mapped[Optional[float]] = mapped_column(Float)
    fat_100g: Mapped[Optional[float]] = mapped_column(Float)
    saturated_fat_100g: Mapped[Optional[float]] = mapped_column(Float)
    energy_kcal_100g: Mapped[Optional[float]] = mapped_column(Float)
    salt_100g: Mapped[Optional[float]] = mapped_column(Float)
    sodium_100g: Mapped[Optional[float]] = mapped_column(Float)
    nutriscore_grade: Mapped[Optional[str]] = mapped_column(Text)
    nutriscore_score: Mapped[Optional[int]] = mapped_column(Integer)
    nova_group: Mapped[Optional[int]] = mapped_column(Integer)
    data_quality_tags: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text).with_variant(JSON, "sqlite"))
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Semantic search embedding options:
    # 1. JSON fallback for non-pgvector deployments (stores 768 floats as JSON string)
    embedding: Mapped[Optional[str]] = mapped_column(Text, comment="JSON array of embedding floats for pgvector search")
    # 2. Native pgvector column (768-dim for sentence-transformers/multi-qa-mpnet-base-dot-v1)
    if PGVECTOR_AVAILABLE:
        embedding_vec: Mapped[Optional[List[float]]] = mapped_column(Vector(768), comment="Native pgvector column for semantic search")

    __table_args__ = (
        Index("ix_off_products_product_name", "product_name"),
        Index("ix_off_products_brands", "brands"),
        Index("ix_off_products_nutrition_carbs", "carbs_100g"),
    )