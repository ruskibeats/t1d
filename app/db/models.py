"""SQLAlchemy ORM models for the T1D Companion application."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, relationship

from app.db.base import Base


class User(Base):
    """User model for authentication and personalization."""

    __tablename__ = "tbl_users"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Authentication
    email: Mapped[str] = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)
    is_active: Mapped[bool] = Column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)

    # Profile
    full_name: Mapped[str | None] = Column(String(255))
    timezone: Mapped[str] = Column(String(50), default="UTC", nullable=False)
    diabetes_type: Mapped[str | None] = Column(String(50))  # e.g., "Type 1", "Type 2", "LADA"
    diagnosis_date: Mapped[datetime | None] = Column(DateTime)

    # Preferences
    glucose_units: Mapped[str] = Column(String(10), default="mg/dL", nullable=False)  # mg/dL or mmol/L
    target_range_low: Mapped[float] = Column(Float, default=70, nullable=False)
    target_range_high: Mapped[float] = Column(Float, default=180, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    glucose_readings: Mapped[list["GlucoseReading"]] = relationship(
        "GlucoseReading",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    events: Mapped[list["ContextEvent"]] = relationship(
        "ContextEvent",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_glucose_sync: Mapped[datetime | None] = Column(DateTime, nullable=True)

    # Dexcom OAuth2
    dexcom_access_token: Mapped[str | None] = Column(String(2048), nullable=True)
    dexcom_refresh_token: Mapped[str | None] = Column(String(2048), nullable=True)
    dexcom_expires_at: Mapped[datetime | None] = Column(DateTime, nullable=True)

    # Indexes
    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}', name='{self.full_name}')>"


class GlucoseReading(Base):
    """Model for glucose/CGM readings."""

    __tablename__ = "tbl_glucose_readings"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # User reference
    user_id: Mapped[int] = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False)

    # Reading data
    timestamp: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    glucose_value: Mapped[float] = Column(Float, nullable=False)
    glucose_units: Mapped[str] = Column(String(10), default="mg/dL", nullable=False)  # mg/dL or mmol/L

    # Reading type and source
    reading_type: Mapped[str] = Column(String(50), nullable=False)  # "sensor", "fingerstick", "estimated"
    source: Mapped[str] = Column(String(50), nullable=False)  # "dexcom", "nightscout", "manual"
    source_device_id: Mapped[str | None] = Column(String(255))  # Device/transmitter ID

    # Optional trend information
    trend: Mapped[str | None] = Column(String(20))  # "single_up", "double_up", "flat", etc.
    trend_rate: Mapped[float | None] = Column(Float)  # mg/dL per minute

    # Data quality
    is_calibration: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    is_filtered: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    confidence_level: Mapped[int | None] = Column(Integer)  # 0-100

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    raw_data: Mapped[dict | None] = Column(JSON)  # Store raw API response for debugging

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="glucose_readings")

    # Indexes for efficient querying
    __table_args__ = (
        Index("ix_glucose_user_timestamp", "user_id", "timestamp"),
        Index("ix_glucose_user_range", "user_id", "timestamp", "glucose_value"),
        Index("ix_glucose_source_device", "source", "source_device_id"),
    )

    def __repr__(self) -> str:
        return f"<GlucoseReading(id={self.id}, user_id={self.user_id}, value={self.glucose_value}, time={self.timestamp})>"


class ContextEvent(Base):
    """Model for contextual events (meals, insulin, exercise, etc.)."""

    __tablename__ = "tbl_context_events"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # User reference
    user_id: Mapped[int] = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False)

    # Event details
    event_type: Mapped[str] = Column(String(50), nullable=False, index=True)  # "meal", "insulin", "exercise", etc.
    event_subtype: Mapped[str | None] = Column(String(50))  # "breakfast", "rapid_insulin", "cardio", etc.

    # Timestamp
    timestamp: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    duration: Mapped[int | None] = Column(Integer)  # Duration in minutes

    # Event data (type-specific)
    description: Mapped[str | None] = Column(Text)
    notes: Mapped[str | None] = Column(Text)

    # Nutritional data (for meals)
    carbs_grams: Mapped[float | None] = Column(Float)
    protein_grams: Mapped[float | None] = Column(Float)
    fat_grams: Mapped[float | None] = Column(Float)
    calories: Mapped[int | None] = Column(Integer)

    # Medication data (for insulin)
    insulin_units: Mapped[float | None] = Column(Float)
    insulin_type: Mapped[str | None] = Column(String(50))

    # Exercise data
    intensity: Mapped[str | None] = Column(String(20))  # "low", "moderate", "high"
    heart_rate_avg: Mapped[int | None] = Column(Integer)

    # Photo/document references
    photos: Mapped[list | None] = Column(JSON)  # List of file paths or URLs

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    tags: Mapped[list | None] = Column(JSON)  # List of tags

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="events")

    # Indexes
    __table_args__ = (
        Index("ix_event_user_type", "user_id", "event_type"),
        Index("ix_event_user_timestamp", "user_id", "timestamp"),
        Index("ix_event_user_subtype", "user_id", "event_subtype"),
    )

    def __repr__(self) -> str:
        return f"<ContextEvent(id={self.id}, user_id={self.user_id}, type='{self.event_type}', time={self.timestamp})>"


class Conversation(Base):
    """Model for AI conversation history."""

    __tablename__ = "tbl_conversations"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # User reference
    user_id: Mapped[int] = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False)

    # Conversation details
    title: Mapped[str | None] = Column(String(255))

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[list["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class ConversationMessage(Base):
    """Model for individual messages in a conversation."""

    __tablename__ = "tbl_conversation_messages"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # Conversation reference
    conversation_id: Mapped[int] = Column(Integer, ForeignKey("tbl_conversations.id", ondelete="CASCADE"), nullable=False)

    # Message details
    role: Mapped[str] = Column(String(20), nullable=False)  # "user", "assistant", "system"
    content: Mapped[str] = Column(Text, nullable=False)

    # Optional extra data
    extra_data: Mapped[dict | None] = Column(JSON)

    # Timestamps
    timestamp: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index("ix_msg_conversation_time", "conversation_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<ConversationMessage(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class PatternAnalysis(Base):
    """Model for stored pattern analysis results."""

    __tablename__ = "tbl_pattern_analyses"

    # Primary key
    id: Mapped[int] = Column(Integer, primary_key=True, index=True)

    # User reference
    user_id: Mapped[int] = Column(Integer, ForeignKey("tbl_users.id", ondelete="CASCADE"), nullable=False)

    # Analysis details
    pattern_type: Mapped[str] = Column(String(50), nullable=False, index=True)  # "post_meal_spike", "overnight_low", etc.
    time_period: Mapped[str] = Column(String(50), nullable=False)  # "daily", "weekly", "monthly"
    start_date: Mapped[datetime] = Column(DateTime, nullable=False, index=True)
    end_date: Mapped[datetime] = Column(DateTime, nullable=False, index=True)

    # Analysis results
    summary: Mapped[str] = Column(Text, nullable=False)
    findings: Mapped[dict] = Column(JSON, nullable=False)
    statistics: Mapped[dict] = Column(JSON, nullable=False)
    recommendations: Mapped[list | None] = Column(JSON)

    # Metadata
    created_at: Mapped[datetime] = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index("ix_pattern_user_type", "user_id", "pattern_type"),
        Index("ix_pattern_user_period", "user_id", "time_period"),
    )

    def __repr__(self) -> str:
        return f"<PatternAnalysis(id={self.id}, user_id={self.user_id}, type='{self.pattern_type}', period={self.time_period})>"
