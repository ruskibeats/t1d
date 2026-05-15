"""Context events API endpoints."""


from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.models.event import ContextEventCreate, ContextEventResponse

router = APIRouter()


@router.get("/", response_model=list[ContextEventResponse])
async def get_events(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> list[ContextEventResponse]:
    """Get context events for current user."""
    from app.db.models import ContextEvent

    result = await session.execute(
        select(ContextEvent)
        .where(ContextEvent.user_id == user.id)
        .offset(skip)
        .limit(limit)
        .order_by(ContextEvent.timestamp.desc())
    )
    events = result.scalars().all()

    return [ContextEventResponse.model_validate(e) for e in events]


@router.post("/", response_model=ContextEventResponse, status_code=201)
async def create_event(
    event_data: ContextEventCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> ContextEventResponse:
    """Create new context event."""
    from app.db.models import ContextEvent

    event = ContextEvent(
        user_id=user.id,
        event_type=event_data.event_type,
        event_subtype=event_data.event_subtype,
        timestamp=event_data.timestamp,
        duration=event_data.duration,
        description=event_data.description,
        notes=event_data.notes,
        tags=event_data.tags,
    )

    # Set type-specific data
    if event_data.meal_data:
        event.carbs_grams = event_data.meal_data.carbs_grams
        event.protein_grams = event_data.meal_data.protein_grams
        event.fat_grams = event_data.meal_data.fat_grams
        event.calories = event_data.meal_data.calories
    elif event_data.insulin_data:
        event.insulin_units = event_data.insulin_data.insulin_units
        event.insulin_type = event_data.insulin_data.insulin_type
    elif event_data.exercise_data:
        event.intensity = event_data.exercise_data.intensity
        event.heart_rate_avg = event_data.exercise_data.heart_rate_avg

    session.add(event)
    await session.commit()
    await session.refresh(event)

    return ContextEventResponse.model_validate(event)


@router.get("/{event_id}", response_model=ContextEventResponse)
async def get_event(
    event_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> ContextEventResponse:
    """Get specific context event."""
    from app.db.models import ContextEvent

    result = await session.execute(
        select(ContextEvent).where(
            ContextEvent.id == event_id,
            ContextEvent.user_id == user.id,
        )
    )
    event = result.scalar_one_or_none()

    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Event not found")

    return ContextEventResponse.model_validate(event)
