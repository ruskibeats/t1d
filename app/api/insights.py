"""Insights API endpoints for proactive pattern recognition.

Provides endpoints for:
- GET /api/v1/insights — All insights for the current user
- POST /api/v1/insights/predict — Pre-meal prediction
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.models.insight import (
    InsightsResponse,
    PreMealRequest,
    PreMealPrediction,
    TimeOfDayPattern,
    MealPattern,
    GlucoseSummary,
)
from app.services.insights_service import InsightsService

router = APIRouter()
insights_service = InsightsService()


@router.get("/", response_model=InsightsResponse)
async def get_insights(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> InsightsResponse:
    """Get all proactive insights for the current user.

    Returns time-of-day patterns, meal correlations, and glucose summary.
    All insights include safety disclaimers.

    Args:
        session: Database session
        user: Current authenticated user

    Returns:
        Complete insights response

    Raises:
        HTTPException: 500 if insight generation fails
    """
    try:
        result = await insights_service.generate_all_insights(session, user.id)

        # Convert raw dicts to Pydantic models
        time_patterns = [
            TimeOfDayPattern(**p) for p in result.get("time_of_day_patterns", [])
        ]
        meal_patterns = [
            MealPattern(**p) for p in result.get("meal_patterns", [])
        ]
        summary_data = result.get("summary", {})
        summary = GlucoseSummary(**summary_data) if summary_data else None

        return InsightsResponse(
            generated_at=datetime.fromisoformat(result["generated_at"]),
            summary=summary,
            time_of_day_patterns=time_patterns,
            meal_patterns=meal_patterns,
            total_insights=result["total_insights"],
            disclaimer=result["disclaimer"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate insights: {str(e)}",
        )


@router.post("/predict", response_model=PreMealPrediction)
async def predict_meal(
    request: PreMealRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> PreMealPrediction:
    """Predict glucose outcome for a planned meal.

    Uses historical data to predict what will happen when the user
    eats a specific food. Includes current glucose context if provided.

    IMPORTANT: This is a prediction, not medical advice. All responses
    include appropriate disclaimers.

    Args:
        request: Pre-meal prediction request with food name
        session: Database session
        user: Current authenticated user

    Returns:
        Pre-meal prediction with personalized guidance

    Raises:
        HTTPException: 400 if insufficient data for prediction
    """
    try:
        prediction = await insights_service.predict_meal_outcome(
            session=session,
            user_id=user.id,
            food_name=request.food_name,
            current_glucose=request.current_glucose,
        )

        if not prediction:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Not enough historical data for '{request.food_name}'. "
                    f"Log at least 3 meals with this food to get predictions."
                ),
            )

        return PreMealPrediction(**prediction)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}",
        )