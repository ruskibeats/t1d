"""Pattern analysis API endpoints."""

from typing import Any, Dict, List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_active_user
from app.db.models import User, GlucoseReading, ContextEvent
from app.models.pattern import (
    PatternAnalysisCreate,
    PatternAnalysisResponse,
    PatternDetectionRequest,
    PatternDetectionResponse,
    PatternType,
)
from app.services.pattern_service import PatternService, PatternAnalysisError


router = APIRouter()
pattern_service = PatternService()


@router.post("/analyze", response_model=Dict[str, Any])
async def analyze_patterns(
    analysis_request: PatternAnalysisCreate,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> Dict[str, Any]:
    """Analyze glucose patterns for a specific time period.
    
    Performs comprehensive analysis including:
    - Time-in-range (TIR) calculations
    - Post-meal spike detection
    - Overnight hypoglycemia detection
    - Exercise impact analysis
    
    Args:
        analysis_request: Pattern analysis parameters
        session: Database session
        user: Current authenticated user
        
    Returns:
        Comprehensive pattern analysis results
        
    Raises:
        HTTPException: 400 if analysis fails
    """
    try:
        result = await pattern_service.calculate_time_in_range(
            session=session,
            user_id=user.id,
            start_date=analysis_request.start_date,
            end_date=analysis_request.end_date,
        )
        
        # Detect post-meal spikes
        spikes = await pattern_service.detect_post_meal_spikes(
            session=session,
            user_id=user.id,
            start_date=analysis_request.start_date,
            end_date=analysis_request.end_date,
        )
        
        # Detect overnight hypoglycemia
        overnight = await pattern_service.detect_overnight_hypoglycemia(
            session=session,
            user_id=user.id,
            start_date=analysis_request.start_date,
            end_date=analysis_request.end_date,
        )
        
        # Analyze exercise impact
        exercise = await pattern_service.analyze_exercise_impact(
            session=session,
            user_id=user.id,
            start_date=analysis_request.start_date,
            end_date=analysis_request.end_date,
        )
        
        # Correlations
        correlations = await pattern_service.analyze_correlations(
            session=session,
            user_id=user.id,
            start_date=analysis_request.start_date,
            end_date=analysis_request.end_date,
        )
        
        # Build comprehensive response
        return {
            "analysis": {
                "period": result["period"],
                "tir": result["time_in_range"],
                "estimated_a1c": result["estimated_a1c"],
                "grade": result["grade"],
            },
            "statistics": result["readings"],
            "post_meal_spikes": {
                "count": len(spikes),
                "events": spikes,
            },
            "overnight_hypoglycemia": {
                "event_count": len(overnight),
                "events": overnight,
            },
            "exercise_impact": {
                "sessions_analyzed": len(exercise),
                "events": exercise,
            },
            "correlations": [c.model_dump() for c in correlations],
            "recommendations": _generate_overall_recommendations(
                result, spikes, overnight, exercise
            ),
        }
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Pattern analysis failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during pattern analysis: {str(e)}",
        )


@router.post("/detect", response_model=PatternDetectionResponse)
async def detect_patterns(
    detection_request: PatternDetectionRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
) -> PatternDetectionResponse:
    """Detect specific pattern types in glucose data.
    
    Args:
        detection_request: Pattern detection request
        session: Database session
        user: Current authenticated user
        
    Returns:
        Detected patterns with details
        
    Raises:
        HTTPException: 400 if detection fails
    """
    try:
        result = await pattern_service.detect_patterns(
            session=session,
            detection_request=detection_request,
        )
        return result
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Pattern detection failed: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal error during pattern detection: {str(e)}",
        )


@router.post("/tir", response_model=Dict[str, Any])
async def calculate_tir(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
    start_date: datetime = None,
    end_date: datetime = None,
) -> Dict[str, Any]:
    """Calculate time-in-range statistics.
    
    Args:
        session: Database session
        user: Current authenticated user
        start_date: Start date (defaults to 14 days ago)
        end_date: End date (defaults to now)
        
    Returns:
        TIR statistics
        
    Raises:
        HTTPException: 400 if calculation fails
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    if start_date is None:
        start_date = end_date - timedelta(days=14)
    
    try:
        result = await pattern_service.calculate_time_in_range(
            session=session,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
        )
        return result
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"TIR calculation failed: {str(e)}",
        )


@router.post("/spikes", response_model=Dict[str, Any])
async def detect_spikes(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
    min_carbs: float = 30,
    start_date: datetime = None,
    end_date: datetime = None,
) -> Dict[str, Any]:
    """Detect post-meal glucose spikes.
    
    Args:
        session: Database session
        user: Current authenticated user
        min_carbs: Minimum carbs to consider (default 30g)
        start_date: Start date
        end_date: End date
        
    Returns:
        Detected post-meal spikes
        
    Raises:
        HTTPException: 400 if detection fails
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    try:
        spikes = await pattern_service.detect_post_meal_spikes(
            session=session,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
            min_carbs=min_carbs,
        )
        
        return {
            "count": len(spikes),
            "spikes": spikes,
        }
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Spike detection failed: {str(e)}",
        )


@router.post("/overnight", response_model=Dict[str, Any])
async def detect_overnight_lows(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
    start_date: datetime = None,
    end_date: datetime = None,
) -> Dict[str, Any]:
    """Detect overnight hypoglycemia.
    
    Args:
        session: Database session
        user: Current authenticated user
        start_date: Start date
        end_date: End date
        
    Returns:
        Detected overnight hypoglycemia events
        
    Raises:
        HTTPException: 400 if detection fails
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    try:
        events = await pattern_service.detect_overnight_hypoglycemia(
            session=session,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "count": len(events),
            "events": events,
        }
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Overnight detection failed: {str(e)}",
        )


@router.post("/exercise", response_model=Dict[str, Any])
async def analyze_exercise(
    session: AsyncSession = Depends(get_db),
    user: User = Depends(require_active_user),
    start_date: datetime = None,
    end_date: datetime = None,
) -> Dict[str, Any]:
    """Analyze exercise impact on glucose.
    
    Args:
        session: Database session
        user: Current authenticated user
        start_date: Start date
        end_date: End date
        
    Returns:
        Exercise impact analysis
        
    Raises:
        HTTPException: 400 if analysis fails
    """
    if end_date is None:
        end_date = datetime.now(timezone.utc)
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    
    try:
        impacts = await pattern_service.analyze_exercise_impact(
            session=session,
            user_id=user.id,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "count": len(impacts),
            "impacts": impacts,
        }
        
    except PatternAnalysisError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Exercise analysis failed: {str(e)}",
        )


def _generate_overall_recommendations(
    tir_result: Dict[str, Any],
    spikes: List[Dict],
    overnight: List[Dict],
    exercise: List[Dict],
) -> List[str]:
    """Generate overall recommendations based on pattern analysis."""
    recs = []
    pct_in_range = tir_result["time_in_range"]["percentage"]
    if pct_in_range < 50:
        recs.append("Time in range is below 50%. Consider reviewing basal rates and insulin-to-carb ratios with your diabetes team.")
    elif pct_in_range < 70:
        recs.append("Time in range could be improved. Small adjustments to meal timing or insulin dosing may help.")
    else:
        recs.append("Good time in range! Keep up the consistent management.")
    if len(spikes) > 5:
        recs.append(f"Frequent post-meal spikes detected ({len(spikes)} spikes). Consider pre-bolusing and reducing meal carbs.")
    elif len(spikes) > 0:
        recs.append(f"Some post-meal spikes detected. Try pre-bolusing for high-carb meals.")
    if len(overnight) > 0:
        recs.append(f"Overnight lows detected ({len(overnight)} nights). Consider reducing evening basal insulin or bedtime snack.")
    if len(exercise) > 0:
        recs.append(f"Exercise impacts detected. Monitor glucose closely before, during, and after exercise sessions.")
    recs.append("Review patterns with your diabetes care team for personalized adjustments.")
    recs.append("Consider continuous glucose monitoring data trends for additional insights.")
    return recs