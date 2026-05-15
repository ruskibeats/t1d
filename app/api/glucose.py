"""Glucose data API endpoints."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User
from app.models.glucose import (
    GlucoseReadingCreate,
    GlucoseReadingResponse,
    GlucoseStats,
    GlucoseTrend,
)

router = APIRouter()


@router.get("/", response_model=list[GlucoseReadingResponse])
async def get_glucose_readings(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 100,
    skip: int = 0,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> list[GlucoseReadingResponse]:
    """Get glucose readings for current user.
    
    Args:
        start_time: Filter readings after this time
        end_time: Filter readings before this time
        limit: Maximum number of readings to return
        skip: Number of readings to skip
        session: Database session
        user: Current authenticated user
        
    Returns:
        List[GlucoseReadingResponse]: List of glucose readings
    """
    query = select(GlucoseReading).where(
        GlucoseReading.user_id == user.id
    )

    if start_time:
        query = query.where(GlucoseReading.timestamp >= start_time)
    if end_time:
        query = query.where(GlucoseReading.timestamp <= end_time)

    query = query.order_by(GlucoseReading.timestamp.desc())

    if skip:
        query = query.offset(skip)
    if limit:
        query = query.limit(limit)

    result = await session.execute(query)
    readings = result.scalars().all()

    return [GlucoseReadingResponse.model_validate(r) for r in readings]


@router.get("/latest", response_model=GlucoseReadingResponse)
async def get_latest_glucose(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> GlucoseReadingResponse:
    """Get most recent glucose reading.
    
    Args:
        session: Database session
        user: Current authenticated user
        
    Returns:
        GlucoseReadingResponse: Latest glucose reading
        
    Raises:
        HTTPException: 404 if no readings found
    """
    result = await session.execute(
        select(GlucoseReading)
        .where(GlucoseReading.user_id == user.id)
        .order_by(GlucoseReading.timestamp.desc())
        .limit(1)
    )
    reading = result.scalar_one_or_none()

    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No glucose readings found",
        )

    return GlucoseReadingResponse.model_validate(reading)


@router.post("/", response_model=GlucoseReadingResponse, status_code=status.HTTP_201_CREATED)
async def create_glucose_reading(
    reading_data: GlucoseReadingCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> GlucoseReadingResponse:
    """Create new glucose reading.
    
    Args:
        reading_data: Glucose reading data
        session: Database session
        user: Current authenticated user
        
    Returns:
        GlucoseReadingResponse: Created glucose reading
    """
    from app.db.models import GlucoseReading

    reading = GlucoseReading(
        user_id=user.id,
        glucose_value=reading_data.glucose_value,
        glucose_units=reading_data.glucose_units,
        timestamp=reading_data.timestamp,
        reading_type=reading_data.reading_type,
        source=reading_data.source,
        source_device_id=reading_data.source_device_id,
        trend=reading_data.trend,
        trend_rate=reading_data.trend_rate,
        is_calibration=reading_data.is_calibration,
        is_filtered=reading_data.is_filtered,
        confidence_level=reading_data.confidence_level,
    )

    session.add(reading)
    await session.commit()
    await session.refresh(reading)

    return GlucoseReadingResponse.model_validate(reading)


@router.get("/{reading_id}", response_model=GlucoseReadingResponse)
async def get_glucose_reading(
    reading_id: int,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> GlucoseReadingResponse:
    """Get specific glucose reading.
    
    Args:
        reading_id: Glucose reading ID
        session: Database session
        user: Current authenticated user
        
    Returns:
        GlucoseReadingResponse: Glucose reading
        
    Raises:
        HTTPException: 404 if reading not found or access denied
    """
    result = await session.execute(
        select(GlucoseReading)
        .where(
            GlucoseReading.id == reading_id,
            GlucoseReading.user_id == user.id,
        )
    )
    reading = result.scalar_one_or_none()

    if not reading:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Glucose reading not found",
        )

    return GlucoseReadingResponse.model_validate(reading)


@router.get("/{reading_id}/trend", response_model=list[GlucoseTrend])
async def get_glucose_trend(
    reading_id: int,
    window_minutes: int = 120,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> list[GlucoseTrend]:
    """Get glucose trend around specific reading.
    
    Args:
        reading_id: Reference glucose reading ID
        window_minutes: Time window in minutes (before and after)
        session: Database session
        user: Current authenticated user
        
    Returns:
        List[GlucoseTrend]: Glucose trend data points
        
    Raises:
        HTTPException: 404 if reading not found
    """
    from app.db.models import GlucoseReading

    # Get reference reading
    result = await session.execute(
        select(GlucoseReading)
        .where(
            GlucoseReading.id == reading_id,
            GlucoseReading.user_id == user.id,
        )
    )
    reference = result.scalar_one_or_none()

    if not reference:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference glucose reading not found",
        )

    # Calculate time window
    start_time = reference.timestamp - timedelta(minutes=window_minutes)
    end_time = reference.timestamp + timedelta(minutes=window_minutes)

    # Get readings in window
    result = await session.execute(
        select(GlucoseReading)
        .where(
            GlucoseReading.user_id == user.id,
            GlucoseReading.timestamp >= start_time,
            GlucoseReading.timestamp <= end_time,
        )
        .order_by(GlucoseReading.timestamp)
    )
    readings = result.scalars().all()

    return [GlucoseTrend.model_validate(r) for r in readings]


@router.get("/stats/", response_model=GlucoseStats)
async def get_glucose_statistics(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> GlucoseStats:
    """Get glucose statistics for time range.
    
    Args:
        start_time: Start of time range
        end_time: End of time range
        session: Database session
        user: Current authenticated user
        
    Returns:
        GlucoseStats: Glucose statistics
    """
    from sqlalchemy import func, select

    from app.db.models import GlucoseReading

    # Build query
    query = select(
        func.avg(GlucoseReading.glucose_value).label("average"),
        func.min(GlucoseReading.glucose_value).label("min_value"),
        func.max(GlucoseReading.glucose_value).label("max_value"),
        func.stddev(GlucoseReading.glucose_value).label("std_dev"),
        func.count(GlucoseReading.id).label("total_readings"),
    ).where(GlucoseReading.user_id == user.id)

    if start_time:
        query = query.where(GlucoseReading.timestamp >= start_time)
    if end_time:
        query = query.where(GlucoseReading.timestamp <= end_time)

    result = await session.execute(query)
    row = result.one()

    # Calculate time in range
    target_low = user.target_range_low
    target_high = user.target_range_high

    range_query = select(
        func.count(GlucoseReading.id)
    ).where(
        GlucoseReading.user_id == user.id,
        GlucoseReading.glucose_value >= target_low,
        GlucoseReading.glucose_value <= target_high,
    )

    if start_time:
        range_query = range_query.where(GlucoseReading.timestamp >= start_time)
    if end_time:
        range_query = range_query.where(GlucoseReading.timestamp <= end_time)

    range_result = await session.execute(range_query)
    in_range_count = range_result.scalar()

    total = row.total_readings or 0
    in_range = in_range_count or 0
    below = 0
    above = 0

    if total > 0:
        below_query = select(func.count(GlucoseReading.id)).where(
            GlucoseReading.user_id == user.id,
            GlucoseReading.glucose_value < target_low,
        )
        if start_time:
            below_query = below_query.where(GlucoseReading.timestamp >= start_time)
        if end_time:
            below_query = below_query.where(GlucoseReading.timestamp <= end_time)

        below_result = await session.execute(below_query)
        below = below_result.scalar() or 0
        above = total - in_range - below

    return GlucoseStats(
        average=row.average or 0,
        min_value=row.min_value or 0,
        max_value=row.max_value or 0,
        std_dev=row.std_dev or 0,
        time_in_range=(in_range / total * 100) if total > 0 else 0,
        time_below_range=(below / total * 100) if total > 0 else 0,
        time_above_range=(above / total * 100) if total > 0 else 0,
        total_readings=total,
    )
