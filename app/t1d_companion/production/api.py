"""FastAPI endpoints for the production T1D Companion service."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.t1d_companion.production.schemas import (
    CompanionRequest, CompanionResponse, Intent, GlucoseContext, Trend, AnchorType,
)
from app.t1d_companion.production.service import CompanionService, _num
from app.t1d_companion.production.repositories import LRUCache

router = APIRouter(prefix="/companion", tags=["companion"])

# ── Shared service instance (in production, use dependency injection) ──
_service: CompanionService | None = None


async def get_service() -> CompanionService:
    global _service
    if _service is None:
        _service = CompanionService(food_cache=LRUCache(capacity=5000, ttl_seconds=1800))
    return _service


@router.get("/health")
async def health():
    """Health check with cache stats."""
    svc = await get_service()
    return {
        "status": "ok",
        "stats": svc.stats,
    }


@router.post("/process", response_model=CompanionResponse)
async def process_request(
    request: CompanionRequest,
    svc: CompanionService = Depends(get_service),
):
    """Process a companion request end-to-end."""
    if not request.request_id:
        request.request_id = str(uuid.uuid4())
    try:
        result = await svc.process(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process/simulator", response_model=CompanionResponse)
async def process_simulator(
    scenario: str,
    anchor_type: Optional[str] = None,
    svc: CompanionService = Depends(get_service),
):
    """Quick simulator endpoint — random profile, no CGM context needed."""
    request = CompanionRequest(
        scenario=scenario,
        user_id="simulator",
        intent=Intent.MEAL_PREDICTION,
        anchor_type=AnchorType(anchor_type) if anchor_type else None,
        request_id=str(uuid.uuid4()),
    )
    try:
        result = await svc.process(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def stats(svc: CompanionService = Depends(get_service)):
    """Service statistics for monitoring."""
    return svc.stats