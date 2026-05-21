"""FastAPI routes for the simulator pipeline.

Provides endpoints to:
- Create, list, and inspect simulation runs
- Start a run (generate → write → detect → evaluate)
- Query hidden truths and detector scores
- List anchor profiles
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging_config import get_logger
from app.core.security import require_active_user
from app.db.models import User
from app.simulator.anchors import (
    ANCHOR_PARAMETER_RANGES,
    anchor_description,
    anchor_label,
    list_anchor_profiles,
)
from app.simulator.evaluator import SimulatorEvaluator
from app.simulator.schemas import (
    AnchorType,
    EvaluationSummary,
    RunStatus,
    SimRunCreate,
    SimRunListResponse,
    SimRunResponse,
    SimUserResponse,
)
from app.simulator.service import SimulationService

logger = get_logger(__name__)
router = APIRouter(prefix="/simulator", tags=["simulator"])


# ── Anchor Profiles ──


@router.get(
    "/anchors",
    summary="List all anchor profiles",
    description="Returns the 12 anchor archetype definitions with parameter ranges.",
)
async def list_anchors() -> list[dict[str, Any]]:
    """List all anchor profiles with their parameter ranges."""
    profiles = list_anchor_profiles()
    return [
        {
            "type": p.anchor_type.value,
            "label": anchor_label(p.anchor_type),
            "description": anchor_description(p.anchor_type),
            "parameter_ranges": {
                "basal_glucose_mean": list(p.basal_glucose_mean),
                "basal_glucose_amplitude": list(p.basal_glucose_amplitude),
                "meal_rise_factor": list(p.meal_rise_factor),
                "insulin_sensitivity": list(p.insulin_sensitivity),
                "carb_ratio": list(p.carb_ratio),
                "hypo_risk": list(p.hypo_risk),
                "noise_sd": list(p.noise_sd),
                "exercise_drop_factor": list(p.exercise_drop_factor),
                "dawn_effect_strength": list(p.dawn_effect_strength),
                "fat_delay_hours": list(p.fat_delay_hours),
                "variability_cv": list(p.variability_cv),
            },
        }
        for p in profiles
    ]


# ── Simulation Runs ──


@router.post(
    "/runs",
    status_code=status.HTTP_201_CREATED,
    response_model=SimRunResponse,
    summary="Create a simulation run",
    description="Creates a new simulation run. Use POST /simulator/runs/{id}/start to execute it.",
)
async def create_sim_run(
    data: SimRunCreate,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunResponse:
    service = SimulationService(db)
    run = await service.create_run(data, created_by=user.id)
    return SimRunResponse.model_validate(run)


@router.get(
    "/runs",
    response_model=SimRunListResponse,
    summary="List simulation runs",
)
async def list_sim_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, description="Filter by status"),
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunListResponse:
    service = SimulationService(db)
    runs, total = await service.list_runs(limit=limit, offset=offset, status=status)
    return SimRunListResponse(
        runs=[SimRunResponse.model_validate(r) for r in runs],
        total=total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=SimRunResponse,
    summary="Get simulation run details",
)
async def get_sim_run(
    run_id: int,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunResponse:
    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Simulation run {run_id} not found")
    return SimRunResponse.model_validate(run)


@router.post(
    "/runs/{run_id}/start",
    response_model=SimRunResponse,
    summary="Start a simulation run",
    description="Executes the full simulation pipeline: generate patients, write data, "
                "run detectors, evaluate. Returns when complete (may take minutes for large runs).",
)
async def start_sim_run(
    run_id: int,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> SimRunResponse:
    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Simulation run {run_id} not found")

    if run.status not in (RunStatus.PENDING.value, RunStatus.FAILED.value):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Run {run_id} is already in status '{run.status}'. "
            f"Only 'pending' or 'failed' runs can be started.",
        )

    try:
        run = await service.start_run(run_id)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

    return SimRunResponse.model_validate(run)


# ── Simulation Users ──


@router.get(
    "/runs/{run_id}/users",
    response_model=list[SimUserResponse],
    summary="List sim users for a run",
)
async def list_sim_users(
    run_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[SimUserResponse]:
    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Simulation run {run_id} not found")

    users, _ = await service.get_run_users(run_id, limit=limit, offset=offset)
    return [SimUserResponse.model_validate(u) for u in users]


# ── Evaluation ──


@router.get(
    "/runs/{run_id}/evaluation",
    response_model=EvaluationSummary,
    summary="Get evaluation results for a run",
)
async def get_evaluation(
    run_id: int,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> EvaluationSummary:
    """Get aggregated evaluation results for a completed simulation run."""
    from app.simulator.models import SimDetectorScore, SimHiddenTruth, SimRun

    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Simulation run {run_id} not found")

    if run.status != RunStatus.COMPLETED.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Run {run_id} is in status '{run.status}'. Evaluation requires 'completed' status.",
        )

    # Build evaluation summary from stored data
    truths = await service.get_truths(run_id)
    scores = await service.get_scores(run_id)

    # Count detection stats
    total_truths = len(truths)
    truths_detected = sum(1 for t in truths if t.is_detected)
    truths_missed = total_truths - truths_detected
    detection_rate = truths_detected / total_truths if total_truths > 0 else 0.0
    avg_confidence = (
        sum(t.detector_confidence for t in truths if t.is_detected and t.detector_confidence is not None)
        / truths_detected
        if truths_detected > 0 else 0.0
    )

    # Group by pattern type
    from collections import defaultdict
    by_pattern: dict = defaultdict(lambda: {"total": 0, "detected": 0})
    for t in truths:
        by_pattern[t.pattern_type]["total"] += 1
        if t.is_detected:
            by_pattern[t.pattern_type]["detected"] += 1

    pattern_summary = {}
    for ptype, counts in sorted(by_pattern.items()):
        d = counts["detected"]
        t = counts["total"]
        pattern_summary[ptype] = {
            "total": t,
            "detected": d,
            "missed": t - d,
            "detection_rate": round(d / t, 3) if t > 0 else 0,
        }

    # Group by anchor type
    from app.simulator.models import SimUser

    user_result = await db.execute(
        select(SimUser).where(SimUser.sim_run_id == run_id)
    )
    sim_users = list(user_result.scalars().all())
    user_map = {u.id: u.anchor_type for u in sim_users}

    by_anchor: dict = defaultdict(lambda: {"total": 0, "detected": 0})
    for t in truths:
        anchor = user_map.get(t.sim_user_id, "unknown")
        by_anchor[anchor]["total"] += 1
        if t.is_detected:
            by_anchor[anchor]["detected"] += 1

    anchor_summary = {}
    for anchor, counts in sorted(by_anchor.items()):
        d = counts["detected"]
        t = counts["total"]
        anchor_summary[anchor] = {
            "total": t,
            "detected": d,
            "missed": t - d,
            "detection_rate": round(d / t, 3) if t > 0 else 0,
        }

    # Build detector scores dict
    detector_scores: dict[str, float] = {}
    for s in scores:
        detector_scores[s.metric_name] = s.metric_value

    return EvaluationSummary(
        run_id=run.id,
        run_name=run.name,
        status=run.status,
        total_truths=total_truths,
        truths_detected=truths_detected,
        truths_missed=truths_missed,
        detection_rate=round(detection_rate, 3),
        avg_confidence_detected=round(avg_confidence, 3),
        by_pattern_type=pattern_summary,
        by_anchor_type=anchor_summary,
        detector_scores=detector_scores,
        calibration=run.summary_json.get("calibration") if run.summary_json else None,
    )


@router.get(
    "/runs/{run_id}/truths",
    summary="List hidden truths for a run",
    description="Returns planted hidden truths. Optionally filtered by user and pattern type.",
)
async def get_hidden_truths(
    run_id: int,
    sim_user_id: Optional[int] = Query(None),
    pattern_type: Optional[str] = Query(None),
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    from app.simulator.models import SimHiddenTruth

    query = select(SimHiddenTruth).where(SimHiddenTruth.sim_run_id == run_id)
    if sim_user_id:
        query = query.where(SimHiddenTruth.sim_user_id == sim_user_id)
    if pattern_type:
        query = query.where(SimHiddenTruth.pattern_type == pattern_type)
    query = query.order_by(SimHiddenTruth.pattern_type, SimHiddenTruth.window_start)

    result = await db.execute(query)
    truths = list(result.scalars().all())
    return [
        {
            "id": t.id,
            "sim_user_id": t.sim_user_id,
            "pattern_type": t.pattern_type,
            "subtype": t.subtype,
            "window_start": t.window_start,
            "window_end": t.window_end,
            "expected_peak_delta": t.expected_peak_delta,
            "expected_time_to_peak_min": t.expected_time_to_peak_min,
            "is_detected": t.is_detected,
            "detector_confidence": t.detector_confidence,
        }
        for t in truths
    ]


@router.get(
    "/runs/{run_id}/calibration",
    summary="Get confidence calibration for a run",
    description="Returns ECE, per-bin accuracy, and threshold recommendations "
                "for each detector pattern type. Requires a completed run.",
)
async def get_calibration(
    run_id: int,
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get confidence calibration summary for a completed simulation run.

    Returns binned calibration curves, ECE per pattern type,
    and minimum confidence thresholds for deployment.
    """
    from app.simulator.models import SimRun

    result = await db.execute(select(SimRun).where(SimRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Simulation run {run_id} not found")
    if run.status != RunStatus.COMPLETED.value:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Run {run_id} is in status '{run.status}'. Calibration requires 'completed' status.",
        )

    calibration = (run.summary_json or {}).get("calibration")
    if not calibration:
        return {
            "run_id": run_id,
            "status": "calibration_not_available",
            "message": "This run was completed before calibration was added. Re-run to get calibration data.",
        }

    return {
        "run_id": run_id,
        "run_name": run.name,
        "status": "completed",
        "calibration": calibration,
    }


@router.get(
    "/runs/{run_id}/scores",
    summary="List detector scores for a run",
)
async def get_detector_scores(
    run_id: int,
    anchor_type: Optional[str] = Query(None),
    pattern_type: Optional[str] = Query(None),
    user: User = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    service = SimulationService(db)
    scores = await service.get_scores(run_id, anchor_type=anchor_type, pattern_type=pattern_type)
    return [
        {
            "id": s.id,
            "sim_user_id": s.sim_user_id,
            "detector_name": s.detector_name,
            "detector_version": s.detector_version,
            "anchor_type": s.anchor_type,
            "pattern_type": s.pattern_type,
            "metric_name": s.metric_name,
            "metric_value": s.metric_value,
            "breakdown_json": s.breakdown_json,
        }
        for s in scores
    ]
