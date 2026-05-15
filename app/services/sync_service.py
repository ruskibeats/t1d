"""Background sync and data synchronization service.

Manages periodic synchronization of glucose data from external sources
(Dexcom, Nightscout) using Celery background tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from celery import Celery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_token
from app.db.models import User, GlucoseReading
from app.services.dexcom_service import (
    DexcomService,
    DexcomServiceError,
    DexcomOAuthTokens,
)
from app.services.nightscout_service import (
    NightscoutService,
    NightscoutServiceError,
)
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Celery Configuration
# ---------------------------------------------------------------------------

def make_celery() -> Celery:
    """Create and configure Celery application.
    
    Returns:
        Configured Celery app
    """
    # Redis URL from environment
    redis_url = "redis://redis:6379/0"
    
    celery_app = Celery(
        "t1d_sync",
        broker=redis_url,
        backend=f"{redis_url}/1",
        include=["app.services.sync_service"],
    )
    
    # Celery configuration
    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=300,  # 5 minutes
        task_soft_time_limit=240,  # 4 minutes
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        beat_schedule={
            # Sync glucose data every 5 minutes
            "sync-glucose-every-5min": {
                "task": "app.services.sync_service.sync_all_users_glucose",
                "schedule": 300.0,  # 5 minutes
            },
            # Deep sync (24h) once per hour
            "deep-sync-hourly": {
                "task": "app.services.sync_service.deep_sync_all_users",
                "schedule": 3600.0,  # 1 hour
            },
        },
    )
    
    return celery_app


celery_app = make_celery()


# ---------------------------------------------------------------------------
# Database Session for Celery Tasks
# ---------------------------------------------------------------------------

async def get_db_session() -> AsyncSession:
    """Get database session for Celery tasks.
    
    Returns:
        Database session
    """
    # This is a simplified version - in production, you'd need
    # proper async context management
    return next(get_db())


# ---------------------------------------------------------------------------
# Sync Task Models
# ---------------------------------------------------------------------------

class SyncResult(BaseModel):
    """Result of a sync operation."""
    
    user_id: int
    source: str  # "dexcom" or "nightscout"
    new_readings: int
    updated_at: datetime
    success: bool
    error: Optional[str] = None


class UserSyncConfig(BaseModel):
    """Configuration for user's data sources."""
    
    user_id: int
    dexcom_enabled: bool = False
    dexcom_access_token: Optional[str] = None
    dexcom_refresh_token: Optional[str] = None
    dexcom_expires_at: Optional[datetime] = None
    nightscout_enabled: bool = False
    nightscout_url: Optional[str] = None
    nightscout_token: Optional[str] = None
    last_sync: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Sync Tasks
# ---------------------------------------------------------------------------

@celery_app.task(bind=True, name="sync_user_glucose")
def sync_user_glucose_task(
    self,
    user_id: int,
    source: str,
) -> Dict[str, Any]:
    """Background task to sync glucose data for a single user.
    
    Args:
        user_id: ID of the user to sync
        source: Data source ("dexcom" or "nightscout")
        
    Returns:
        Sync result as dictionary
    """
    logger.info(f"Starting sync task for user {user_id} from {source}")
    
    try:
        # Run async sync in event loop
        result = asyncio.run(_sync_user_glucose_async(user_id, source))
        return result
    except Exception as e:
        logger.error(f"Sync task failed for user {user_id}: {e}")
        return {
            "user_id": user_id,
            "source": source,
            "new_readings": 0,
            "updated_at": datetime.now(timezone.utc),
            "success": False,
            "error": str(e),
        }


async def _sync_user_glucose_async(
    user_id: int,
    source: str,
) -> Dict[str, Any]:
    """Async implementation of user glucose sync.
    
    Args:
        user_id: ID of the user
        source: Data source
        
    Returns:
        Sync result
    """
    from app.config import get_settings
    settings = get_settings()
    
    async for session in get_db():
        # Get user
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        new_readings = 0
        
        if source == "dexcom" and user.dexcom_access_token:
            # Check if token needs refresh
            if (
                user.dexcom_expires_at
                and user.dexcom_expires_at < datetime.now(timezone.utc)
                and user.dexcom_refresh_token
            ):
                # Refresh token
                dexcom = DexcomService(
                    client_id=settings.DEXCOM_CLIENT_ID,
                    client_secret=settings.DEXCOM_CLIENT_SECRET,
                    redirect_uri=settings.DEXCOM_REDIRECT_URI,
                    use_sandbox=settings.DEXCOM_USE_SANDBOX,
                )
                try:
                    tokens = await dexcom.refresh_access_token(
                        user.dexcom_refresh_token
                    )
                    user.dexcom_access_token = tokens.access_token
                    user.dexcom_refresh_token = tokens.refresh_token
                    user.dexcom_expires_at = datetime.now(
                        timezone.utc
                    ) + timedelta(seconds=tokens.expires_in)
                    await session.commit()
                except DexcomServiceError as e:
                    logger.error(f"Token refresh failed for user {user_id}: {e}")
                    return {
                        "user_id": user_id,
                        "source": source,
                        "new_readings": 0,
                        "updated_at": datetime.now(timezone.utc),
                        "success": False,
                        "error": f"Token refresh failed: {str(e)}",
                    }
            
            # Sync data
            if user.dexcom_access_token:
                dexcom = DexcomService(
                    client_id=settings.DEXCOM_CLIENT_ID,
                    client_secret=settings.DEXCOM_CLIENT_SECRET,
                    redirect_uri=settings.DEXCOM_REDIRECT_URI,
                    use_sandbox=settings.DEXCOM_USE_SANDBOX,
                )
                try:
                    new_readings = await dexcom.sync_recent_data(
                        session, user, user.dexcom_access_token
                    )
                except DexcomServiceError as e:
                    logger.error(f"Dexcom sync failed for user {user_id}: {e}")
                    return {
                        "user_id": user_id,
                        "source": source,
                        "new_readings": 0,
                        "updated_at": datetime.now(timezone.utc),
                        "success": False,
                        "error": str(e),
                    }
        
        elif source == "nightscout":
            # Sync from Nightscout
            # Note: In production, you'd store Nightscout URL and token per user
            ns_url = getattr(settings, "NIGHTSCOUT_URL", None)
            ns_token = getattr(settings, "NIGHTSCOUT_API_TOKEN", None)
            
            if ns_url:
                nightscout = NightscoutService(
                    base_url=ns_url,
                    api_token=ns_token,
                )
                try:
                    new_readings = await nightscout.sync_recent_data(
                        session, user
                    )
                except NightscoutServiceError as e:
                    logger.error(f"Nightscout sync failed for user {user_id}: {e}")
                    return {
                        "user_id": user_id,
                        "source": source,
                        "new_readings": 0,
                        "updated_at": datetime.now(timezone.utc),
                        "success": False,
                        "error": str(e),
                    }
        
        else:
            return {
                "user_id": user_id,
                "source": source,
                "new_readings": 0,
                "updated_at": datetime.now(timezone.utc),
                "success": False,
                "error": f"Unknown source: {source}",
            }
        
        return {
            "user_id": user_id,
            "source": source,
            "new_readings": new_readings,
            "updated_at": datetime.now(timezone.utc),
            "success": True,
            "error": None,
        }


@celery_app.task(bind=True, name="sync_all_users_glucose")
def sync_all_users_glucose_task(self) -> List[Dict[str, Any]]:
    """Background task to sync glucose data for all active users.
    
    Returns:
        List of sync results
    """
    logger.info("Starting sync for all users")
    
    try:
        results = asyncio.run(_sync_all_users_glucose_async())
        logger.info(
            f"Sync complete: {sum(1 for r in results if r['success'])} "
            f"successful, {sum(r['new_readings'] for r in results)} new readings"
        )
        return results
    except Exception as e:
        logger.error(f"Sync all users task failed: {e}")
        return []


async def _sync_all_users_glucose_async() -> List[Dict[str, Any]]:
    """Async implementation of sync all users.
    
    Returns:
        List of sync results
    """
    results: List[Dict[str, Any]] = []
    
    async for session in get_db():
        # Get all active users
        result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        
        for user in users:
            # Determine which sources to sync
            sources = []
            if getattr(user, "dexcom_access_token", None):
                sources.append("dexcom")
            
            # For Nightscout, check settings or user preference
            from app.config import get_settings
            settings = get_settings()
            if getattr(settings, "NIGHTSCOUT_URL", None):
                sources.append("nightscout")
            
            # Sync each source
            for source in sources:
                try:
                    result = await _sync_user_glucose_async(user.id, source)
                    results.append(result)
                    
                    # Small delay between sources
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f"Failed to sync user {user.id} from {source}: {e}")
                    results.append({
                        "user_id": user.id,
                        "source": source,
                        "new_readings": 0,
                        "updated_at": datetime.now(timezone.utc),
                        "success": False,
                        "error": str(e),
                    })
    
    return results


@celery_app.task(bind=True, name="deep_sync_all_users")
def deep_sync_all_users_task(self) -> List[Dict[str, Any]]:
    """Deep sync (24 hours) for all users.
    
    Returns:
        List of sync results
    """
    logger.info("Starting deep sync for all users")
    
    try:
        results = asyncio.run(_deep_sync_all_users_async())
        logger.info(
            f"Deep sync complete: {sum(1 for r in results if r['success'])} "
            f"successful, {sum(r['new_readings'] for r in results)} new readings"
        )
        return results
    except Exception as e:
        logger.error(f"Deep sync task failed: {e}")
        return []


async def _deep_sync_all_users_async() -> List[Dict[str, Any]]:
    """Async implementation of deep sync (24 hours).
    
    Returns:
        List of sync results
    """
    results: List[Dict[str, Any]] = []
    
    async for session in get_db():
        # Get all active users
        result = await session.execute(
            select(User).where(User.is_active == True)
        )
        users = result.scalars().all()
        
        for user in users:
            # Only sync Dexcom for deep sync (more data)
            if getattr(user, "dexcom_access_token", None):
                try:
                    from app.config import get_settings
                    settings = get_settings()
                    
                    dexcom = DexcomService(
                        client_id=settings.DEXCOM_CLIENT_ID,
                        client_secret=settings.DEXCOM_CLIENT_SECRET,
                        redirect_uri=settings.DEXCOM_REDIRECT_URI,
                        use_sandbox=settings.DEXCOM_USE_SANDBOX,
                    )
                    
                    async for s in get_db():
                        new_readings = await dexcom.sync_glucose_data(
                            s, user, user.dexcom_access_token, lookback_hours=24
                        )
                        results.append({
                            "user_id": user.id,
                            "source": "dexcom",
                            "new_readings": new_readings,
                            "updated_at": datetime.now(timezone.utc),
                            "success": True,
                            "error": None,
                        })
                        break
                    
                except DexcomServiceError as e:
                    logger.error(f"Deep sync failed for user {user.id}: {e}")
                    results.append({
                        "user_id": user.id,
                        "source": "dexcom",
                        "new_readings": 0,
                        "updated_at": datetime.now(timezone.utc),
                        "success": False,
                        "error": str(e),
                    })
    
    return results


# ---------------------------------------------------------------------------
# Manual Sync Functions
# ---------------------------------------------------------------------------

async def trigger_manual_sync(
    user_id: int,
    source: str = "all",
) -> List[SyncResult]:
    """Manually trigger a sync for a user.
    
    Args:
        user_id: User ID
        source: "dexcom", "nightscout", or "all"
        
    Returns:
        List of sync results
    """
    logger.info(f"Manual sync triggered for user {user_id}, source={source}")
    
    results: List[SyncResult] = []
    sources = ["dexcom", "nightscout"] if source == "all" else [source]
    
    for src in sources:
        task_result = sync_user_glucose_task.delay(user_id, src)
        # Wait for result (blocking)
        result_dict = task_result.get(timeout=60)
        results.append(SyncResult(**result_dict))
    
    return results


async def get_sync_status(user_id: int) -> Dict[str, Any]:
    """Get sync status for a user.
    
    Args:
        user_id: User ID
        
    Returns:
        Sync status information
    """
    async for session in get_db():
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"error": "User not found"}
        
        return {
            "user_id": user_id,
            "dexcom_enabled": bool(getattr(user, "dexcom_access_token", None)),
            "dexcom_expires_at": getattr(user, "dexcom_expires_at", None),
            "last_sync": getattr(user, "last_glucose_sync", None),
        }


# ---------------------------------------------------------------------------
# Task Monitoring
# ---------------------------------------------------------------------------

@celery_app.task(bind=True)
def get_task_status(self, task_id: str) -> Dict[str, Any]:
    """Get status of a Celery task.
    
    Args:
        task_id: Celery task ID
        
    Returns:
        Task status information
    """
    from celery.result import AsyncResult
    
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "traceback": result.traceback,
    }


# ---------------------------------------------------------------------------
# Health Checks
# ---------------------------------------------------------------------------

async def check_celery_health() -> Dict[str, Any]:
    """Check Celery worker health.
    
    Returns:
        Health status
    """
    try:
        # Check if Celery can accept tasks
        inspect = celery_app.control.inspect()
        
        active = inspect.active()
        stats = inspect.stats()
        
        return {
            "status": "healthy",
            "active_tasks": active,
            "worker_stats": stats,
            "broker_url": celery_app.conf.broker_url,
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

from pydantic import BaseModel, Field
from typing import Any