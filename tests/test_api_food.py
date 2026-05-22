"""Integration tests for the Food API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch

from app.db.models import User


class TestFoodAPI:
    """Tests for /api/v1/food endpoints."""

    @pytest.mark.asyncio
    async def test_create_food(self, db_session, test_user):
        """POST /api/v1/food creates a food entry."""
        from app.api.food import create_food
        from app.food.schemas import FoodCreate

        data = FoodCreate(
            name="Test Food",
            brand_name="Test Brand",
            serving_size=100,
            serving_unit="g",
            calories=250,
            protein=10,
            carbs=30,
            fat=8,
        )

        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            response = await create_food(
                data=data,
                user=test_user,
                db=db_session,
            )

        assert response.name == "Test Food"
        assert response.calories == 250

    @pytest.mark.asyncio
    async def test_list_foods(self, db_session, test_user):
        """GET /api/v1/food returns list of foods."""
        from app.api.food import create_food
        from app.food.schemas import FoodCreate

        data = FoodCreate(name="Listed Food", calories=100)
        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            await create_food(data=data, user=test_user, db=db_session)

        from app.food.service import FoodService
        response = await FoodService(db_session).list_foods(test_user.id, limit=50, offset=0)
        assert isinstance(response, list)
        assert len(response) >= 1

    @pytest.mark.asyncio
    async def test_create_food_entry(self, db_session, test_user):
        """POST /api/v1/food/entries creates a food entry."""
        from app.api.food import create_entry
        from app.food.schemas import FoodEntryCreate
        from datetime import datetime, timezone

        data = FoodEntryCreate(
            food_id=None,
            quantity=1,
            unit="serving",
            entry_date=datetime.now(timezone.utc),
            meal_type="lunch",
            food_name="Test Meal",
            calories=300,
        )

        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            response = await create_entry(
                data=data,
                user=test_user,
                db=db_session,
            )

        assert response.meal_type == "lunch"
        assert response.calories == 300

    @pytest.mark.asyncio
    async def test_list_entries(self, db_session, test_user):
        """GET /api/v1/food/entries returns entries."""
        from app.api.food import list_entries

        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            response = await list_entries(
                user=test_user,
                db=db_session,
            )

        assert isinstance(response, list)

    @pytest.mark.asyncio
    async def test_estimate_meal_impact_endpoint(self, db_session, test_user):
        """POST /api/v1/food/meal-impact returns a forecast payload."""
        from app.api.food import estimate_meal_impact
        from app.food.schemas import MealImpactRequest

        with patch("app.api.food.get_db", return_value=db_session), \
             patch("app.api.food.require_active_user", return_value=test_user):
            response = await estimate_meal_impact(
                data=MealImpactRequest(items=["zzzz no such food"]),
                user=test_user,
                db=db_session,
            )

        assert response["question"] == "Can I eat zzzz no such food now?"
        assert response["unmatched_items"] == ["zzzz no such food"]
        assert "safety_note" in response
