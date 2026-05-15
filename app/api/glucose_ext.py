"""Extended glucose API endpoints - sync and meal linking."""

from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import ContextEvent, GlucoseReading, User
from app.models.event import MealEventData
from app.services.meal_service import MealLogCreate
from app.services.dexcom_service import DexcomService, DexcomServiceError
from app.services.meal_service import MealService, MealNutritionSummary
from app.services.nightscout_service import NightscoutService, NightscoutServiceError


router = APIRouter(prefix="/glucose")


@router.post("/sync/dexcom", response_model=Dict[str, Any])
async def sync_dexcom(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> Dict[str, Any]:
    """Manually trigger Dexcom sync.
    
    Returns number of new glucose readings saved.
    """
    from app.config import get_settings

    settings = get_settings()

    if not user.dexcom_access_token:
        raise HTTPException(
            status_code=400,
            detail="Dexcom not connected. Please connect your Dexcom account first.",
        )

    try:
        dexcom = DexcomService(
            client_id=settings.DEXCOM_CLIENT_ID,
            client_secret=settings.DEXCOM_CLIENT_SECRET,
            redirect_uri=settings.DEXCOM_REDIRECT_URI,
            use_sandbox=settings.DEXCOM_USE_SANDBOX,
        )

        new_readings = await dexcom.sync_recent_data(
            session, user, user.dexcom_access_token
        )

        # Update last sync timestamp
        user.last_glucose_sync = datetime.utcnow()
        await session.commit()

        return {
            "message": f"Sync successful: {new_readings} new readings",
            "new_readings": new_readings,
            "user_id": user.id,
        }

    except DexcomServiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Dexcom sync failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during sync",
        )


@router.post("/sync/nightscout", response_model=Dict[str, Any])
async def sync_nightscout(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> Dict[str, Any]:
    """Manually trigger Nightscout sync."""
    from app.config import get_settings

    settings = get_settings()
    ns_url = getattr(settings, "NIGHTSCOUT_URL", None)

    if not ns_url:
        raise HTTPException(
            status_code=400,
            detail="Nightscout URL not configured",
        )

    try:
        nightscout = NightscoutService(
            base_url=ns_url,
            api_token=getattr(settings, "NIGHTSCOUT_API_TOKEN", None),
        )

        new_readings = await nightscout.sync_recent_data(session, user)

        user.last_glucose_sync = datetime.utcnow()
        await session.commit()

        return {
            "message": f"Sync successful: {new_readings} new readings",
            "new_readings": new_readings,
            "user_id": user.id,
        }

    except NightscoutServiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Nightscout sync failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Internal server error during sync",
        )


@router.get("/sync/status", response_model=Dict[str, Any])
async def get_sync_status(
    user: User = Depends(require_active_user),
) -> Dict[str, Any]:
    """Get user's sync status."""
    return {
        "user_id": user.id,
        "dexcom_enabled": bool(getattr(user, "dexcom_access_token", None)),
        "dexcom_expires_at": getattr(user, "dexcom_expires_at", None),
        "last_glucose_sync": getattr(user, "last_glucose_sync", None),
    }


@router.post(
    "/{reading_id}/link-meal",
    response_model=Dict[str, Any],
    responses={404: {"description": "Reading or meal not found"}},
)
async def link_meal_to_glucose(
    reading_id: int,
    meal: MealLogCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> Dict[str, Any]:
    """Link a meal to a glucose reading.
    
    Creates a meal event (as a ContextEvent) and associates it with a glucose reading.
    Useful for analyzing post-meal glucose spikes.
    """
    from app.models.event import MealEventData

    result = await session.execute(
        select(GlucoseReading).where(
            GlucoseReading.id == reading_id,
            GlucoseReading.user_id == user.id,
        )
    )
    reading = result.scalar_one_or_none()

    if not reading:
        raise HTTPException(
            status_code=404,
            detail=f"Glucose reading {reading_id} not found",
        )

    try:
        # Calculate nutrition
        meal_service = MealService()
        nutrition = meal_service.calculate_nutrition_summary(meal.meal_items)

        # Create context event with nutritional data
        event = ContextEvent(
            user_id=user.id,
            event_type="meal",
            event_subtype="logged",
            timestamp=meal.timestamp,
            duration=0,
            notes=meal.notes or "",
            carbs_grams=nutrition.total_carbs,
            protein_grams=nutrition.total_proteins,
            fat_grams=nutrition.total_fats,
            calories=int(nutrition.total_calories),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

        return {
            "message": "Meal linked to glucose reading",
            "reading_id": reading_id,
            "glucose_value": reading.glucose_value,
            "glucose_timestamp": reading.timestamp,
            "meal_event_id": event.id,
            "nutrition": nutrition.model_dump(),
            "analysis": {
                "potential_spike": reading.glucose_value > 180
                and nutrition.total_carbs > 30,
                "time_since_meal": "See meal timestamp",
                "recommendation": (
                    "Consider smaller portions or pre-bolus for high-carb meals"
                    if nutrition.total_carbs > 50
                    else "Good carb control"
                ),
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to link meal: {str(e)}",
        )


@router.get(
    "/{reading_id}/meals",
    response_model=List[Dict],
)
async def get_linked_meals(
    reading_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> List[Dict]:
    """Get meals linked to a glucose reading time window.
    
    Looks for meals within ±2 hours of the reading.
    """
    result = await session.execute(
        select(GlucoseReading).where(
            GlucoseReading.id == reading_id,
            GlucoseReading.user_id == user.id,
        )
    )
    reading = result.scalar_one_or_none()

    if not reading:
        raise HTTPException(
            status_code=404,
            detail=f"Glucose reading {reading_id} not found",
        )

    from datetime import timedelta

    window = timedelta(hours=2)
    start_time = reading.timestamp - window
    end_time = reading.timestamp + window

    result = await session.execute(
        select(ContextEvent)
        .where(
            ContextEvent.user_id == user.id,
            ContextEvent.event_type == "meal",
            ContextEvent.timestamp >= start_time,
            ContextEvent.timestamp <= end_time,
        )
        .order_by(ContextEvent.timestamp)
    )

    meals = []
    for event in result.scalars().all():
        time_diff = (event.timestamp - reading.timestamp).total_seconds() / 60
        meals.append(
            {
                "meal_id": event.id,
                "timestamp": event.timestamp,
                "time_diff_minutes": round(time_diff),
                "carbohydrates": event.carbs_grams,
                "protein_grams": event.protein_grams,
                "fat_grams": event.fat_grams,
                "calories": event.calories,
                "notes": event.notes,
            }
        )

    return meals
