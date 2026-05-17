"""Shared pytest fixtures for T1D Companion tests.

Database Behavior
-----------------
By default, tests run against an in-memory SQLite database with
PostgreSQL type compatibility patches (see ``tests/__init__.py``).

To run against a real PostgreSQL instance, set the env var:

    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/t1d_test

When using Postgres, the full ``Base.metadata.create_all()`` is used
instead of selective table creation, because Postgres handles all types
natively (no JSONB/ENUM compat patches needed).
"""

import os

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import text, types, Column
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Apply SQLite compat patches BEFORE importing models
import sqlalchemy.dialects.postgresql.json as pg_json
from sqlalchemy import types as sa_types

class JSONBCompat(sa_types.JSON):
    __visit_name__ = 'JSONB'

pg_json.JSONB = JSONBCompat
sa_types.JSONB = JSONBCompat

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

def _visit_jsonb(self, type_, **kw):
    return self.visit_JSON(type_, **kw)
SQLiteTypeCompiler.visit_JSONB = _visit_jsonb

def _visit_enum(self, type_, **kw):
    return self.visit_VARCHAR(type_, **kw)
SQLiteTypeCompiler.visit_enum = _visit_enum

def _visit_biginteger(self, type_, **kw):
    return self.visit_INTEGER(type_, **kw)
SQLiteTypeCompiler.visit_BigInteger = _visit_biginteger

from app.db.models import User, GlucoseReading, ContextEvent  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402


_test_engine = None


def _get_db_url() -> str:
    """Return the test database URL from env, defaulting to SQLite in-memory."""
    return os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite+aiosqlite:///:memory:",
    )


def _is_postgres(url: str) -> bool:
    """Check if the database URL points to PostgreSQL."""
    return url.startswith("postgresql")


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create a database engine for test fixtures.

    Uses ``TEST_DATABASE_URL`` env var (or SQLite in-memory default).
    When running against Postgres, creates all tables from
    ``Base.metadata``.  When running against SQLite, creates only
    the subset of tables needed by current tests to work around
    duplicate-index-name issues in unrelated domain models.
    """
    global _test_engine

    db_url = _get_db_url()
    use_postgres = _is_postgres(db_url)

    if use_postgres:
        from app.db.base import Base

        _test_engine = create_async_engine(db_url, echo=False)
        async with _test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
        yield _test_engine
        await _test_engine.dispose()
    else:
        # Import all domain models so their tables are registered
        from app.db.models import (  # noqa: F401
            User, GlucoseReading, ContextEvent, Conversation,
            ConversationMessage, PatternAnalysis,
        )
        from app.exercise.models import ExerciseEntry, ExerciseEntrySet  # noqa: F401
        from app.fasting.models import FastingEntry  # noqa: F401
        from app.food.models import Food, FoodEntry  # noqa: F401
        from app.measurements.models import CustomMeasurement  # noqa: F401
        from app.metrics.models import HealthMetric, HealthDailyAggregate  # noqa: F401
        from app.mood.models import MoodEntry  # noqa: F401
        from app.sleep.models import SleepEntry, SleepStage  # noqa: F401
        from app.water.models import WaterEntry  # noqa: F401

        _test_engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:", echo=False
        )
        async with _test_engine.begin() as conn:
            # Selective table creation: only create tables needed by tests.
            # This avoids duplicate-index-name errors in SQLite for domain
            # models that define both column index=True and explicit Index().
            # Create all tables from Base metadata.
            # Some domain models have duplicate index names (index=True + explicit Index).
            # We handle this by creating tables one at a time and skipping index errors.
            from app.db.base import Base
            for table in Base.metadata.sorted_tables:
                try:
                    await conn.run_sync(table.create, checkfirst=True)
                except Exception as e:
                    if "already exists" in str(e):
                        continue
                    raise
        yield _test_engine
        await _test_engine.dispose()

@pytest_asyncio.fixture(scope="function")
async def db_session(db_engine):
    """Create a fresh database session for each test function."""
    async_session_maker = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_verified=True,
        full_name="Test User",
        timezone="UTC",
        diabetes_type="Type 1",
        glucose_units="mg/dL",
        target_range_low=70.0,
        target_range_high=180.0,
    )
    db_session.add(user)
    await db_session.commit()
    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_2(db_session):
    """Create a second test user for multi-user tests."""
    user = User(
        email="test2@example.com",
        hashed_password="test-hash",
        is_active=True,
        is_verified=True,
        full_name="Test User 2",
        timezone="UTC",
        diabetes_type="Type 1",
    )
    db_session.add(user)
    await db_session.commit()
    return user


# =============================================================================
# Pattern Service Test Fixtures
# =============================================================================

@pytest_asyncio.fixture
async def pattern_service():
    """Create a PatternService instance for testing."""
    from app.services.pattern_service import PatternService
    return PatternService()


@pytest_asyncio.fixture
async def glucose_dataset(db_session, test_user):
    """Create a realistic glucose dataset spanning 2 days (reduced from 7 for speed)."""
    from app.db.models import GlucoseReading
    import random
    random.seed(42)
    
    readings = []
    base = datetime.now(timezone.utc) - timedelta(days=2)
    
    for day in range(2):
        for hour in range(24):
            for minute in range(0, 60, 15):  # Every 15 minutes (reduced from 5)
                base_val = 120
                if 4 <= hour <= 7:
                    base_val += 30 + (hour - 4) * 10
                if hour in [8, 13, 19] and minute < 30:
                    base_val += 60
                if 2 <= hour <= 4:
                    base_val -= 40
                
                value = base_val + random.randint(-15, 15)
                value = max(40, min(350, value))
                
                reading = GlucoseReading(
                    user_id=test_user.id,
                    glucose_value=float(value),
                    glucose_units="mg/dL",
                    timestamp=base + timedelta(days=day, hours=hour, minutes=minute),
                    reading_type="sensor",
                    source="dexcom",
                    trend="flat",
                )
                readings.append(reading)
    
    for r in readings:
        db_session.add(r)
    await db_session.commit()
    return readings


@pytest_asyncio.fixture
async def meal_events(db_session, test_user):
    """Create meal events for spike detection testing."""
    from app.db.models import ContextEvent
    
    meals = [
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="breakfast",
            description="Oatmeal", carbs_grams=45,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=8),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="lunch",
            description="Sandwich", carbs_grams=55,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=13),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="dinner",
            description="Pizza", carbs_grams=80, fat_grams=35, protein_grams=30, calories=850,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=19),
        ),
    ]
    for m in meals:
        db_session.add(m)
    await db_session.commit()
    return meals


@pytest_asyncio.fixture
async def exercise_events(db_session, test_user):
    """Create exercise events for impact testing."""
    from app.db.models import ContextEvent
    
    exercises = [
        ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="moderate", duration=45, heart_rate_avg=140,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=17),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="high", duration=30, heart_rate_avg=165,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=7),
        ),
    ]
    for e in exercises:
        db_session.add(e)
    await db_session.commit()
    return exercises
