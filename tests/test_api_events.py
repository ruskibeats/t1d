"""Integration tests for the events API endpoints with real DB.

Tests list, create (meal, exercise, insulin), detail, and access control.
Uses direct endpoint function calls.
"""

import pytest
from unittest.mock import patch
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.models import ContextEvent


@pytest.mark.asyncio
async def test_list_events(db_session, test_user, meal_events):
    """GET /events/ returns context events for current user."""
    from app.api.events import get_events

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await get_events(
            session=db_session,
            user=test_user,
        )

    assert len(response) >= 3
    assert response[0].event_type == "meal"
    assert response[0].user_id == test_user.id


@pytest.mark.asyncio
async def test_list_events_empty(db_session, test_user):
    """GET /events/ returns empty list when no events exist."""
    from app.api.events import get_events

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await get_events(
            session=db_session,
            user=test_user,
        )

    assert len(response) == 0


@pytest.mark.asyncio
async def test_create_meal_event(db_session, test_user):
    """POST /events/ creates a meal event with carbs."""
    from app.api.events import create_event
    from app.models.event import (
        ContextEventCreate,
        EventType,
        EventSubtype,
        MealEventData,
    )

    now = datetime.now(timezone.utc)
    event_data = ContextEventCreate(
        event_type=EventType.MEAL,
        event_subtype=EventSubtype.LUNCH,
        timestamp=now,
        description="Turkey sandwich with salad",
        notes="Lunch at desk",
        meal_data=MealEventData(
            carbs_grams=45.0,
            protein_grams=25.0,
            fat_grams=10.0,
            calories=380,
        ),
    )

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await create_event(
            event_data=event_data,
            session=db_session,
            user=test_user,
        )

    assert response.event_type == "meal"
    assert response.event_subtype == "lunch"
    assert response.description == "Turkey sandwich with salad"
    assert response.user_id == test_user.id
    assert response.id is not None

    # Verify persisted — the ContextEvent model stores meal data as
    # flat columns (carbs_grams, protein_grams, etc.)
    result = await db_session.execute(
        select(ContextEvent).where(ContextEvent.id == response.id)
    )
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.event_type == "meal"
    # Meal-specific fields
    assert persisted.carbs_grams == 45.0


@pytest.mark.asyncio
async def test_create_exercise_event(db_session, test_user):
    """POST /events/ creates an exercise event."""
    from app.api.events import create_event
    from app.models.event import (
        ContextEventCreate,
        EventType,
        EventSubtype,
        ExerciseEventData,
        Intensity,
    )

    now = datetime.now(timezone.utc)
    event_data = ContextEventCreate(
        event_type=EventType.EXERCISE,
        event_subtype=EventSubtype.CARDIO,
        timestamp=now,
        duration=45,
        description="Morning run",
        exercise_data=ExerciseEventData(
            intensity=Intensity.MODERATE,
            heart_rate_avg=145,
        ),
    )

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await create_event(
            event_data=event_data,
            session=db_session,
            user=test_user,
        )

    assert response.event_type == "exercise"
    assert response.event_subtype == "cardio"
    assert response.duration == 45
    assert response.user_id == test_user.id
    assert response.id is not None

    # Verify persisted
    result = await db_session.execute(
        select(ContextEvent).where(ContextEvent.id == response.id)
    )
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.event_type == "exercise"
    assert persisted.duration == 45


@pytest.mark.asyncio
async def test_create_insulin_event(db_session, test_user):
    """POST /events/ creates an insulin event."""
    from app.api.events import create_event
    from app.models.event import (
        ContextEventCreate,
        EventType,
        EventSubtype,
        InsulinEventData,
    )

    now = datetime.now(timezone.utc)
    event_data = ContextEventCreate(
        event_type=EventType.INSULIN,
        event_subtype=EventSubtype.BOLUS,
        timestamp=now,
        description="Pre-meal bolus",
        insulin_data=InsulinEventData(
            insulin_units=5.0,
            insulin_type="rapid",
        ),
    )

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await create_event(
            event_data=event_data,
            session=db_session,
            user=test_user,
        )

    assert response.event_type == "insulin"
    assert response.event_subtype == "bolus"
    assert response.user_id == test_user.id
    assert response.id is not None

    # Verify persisted
    result = await db_session.execute(
        select(ContextEvent).where(ContextEvent.id == response.id)
    )
    persisted = result.scalar_one_or_none()
    assert persisted is not None
    assert persisted.event_type == "insulin"


@pytest.mark.asyncio
async def test_get_event_detail(db_session, test_user, meal_events):
    """GET /events/{id} returns specific event."""
    from app.api.events import get_event

    result = await db_session.execute(
        select(ContextEvent)
        .where(ContextEvent.user_id == test_user.id)
        .limit(1)
    )
    first = result.scalar_one()

    with patch("app.api.events.require_active_user", return_value=test_user):
        response = await get_event(
            event_id=first.id,
            session=db_session,
            user=test_user,
        )

    assert response.id == first.id
    assert response.event_type == first.event_type
    assert response.user_id == test_user.id


@pytest.mark.asyncio
async def test_get_event_not_found(db_session, test_user):
    """GET /events/{id} returns 404 for nonexistent event."""
    from app.api.events import get_event
    from fastapi import HTTPException

    with patch("app.api.events.require_active_user", return_value=test_user):
        with pytest.raises(HTTPException) as exc_info:
            await get_event(
                event_id=99999,
                session=db_session,
                user=test_user,
            )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_event_other_user_not_visible(db_session, test_user, test_user_2, meal_events):
    """Events from one user are not visible to another user."""
    from app.api.events import get_event
    from fastapi import HTTPException

    result = await db_session.execute(
        select(ContextEvent)
        .where(ContextEvent.user_id == test_user.id)
        .limit(1)
    )
    first = result.scalar_one()

    with patch("app.api.events.require_active_user", return_value=test_user_2):
        with pytest.raises(HTTPException) as exc_info:
            await get_event(
                event_id=first.id,
                session=db_session,
                user=test_user_2,
            )

    assert exc_info.value.status_code == 404