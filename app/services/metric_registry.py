"""MetricRegistry - Consolidated dual-write pattern for health metrics.

This module provides a single interface for recording health metrics with
consistent dual-write behavior across all domain services.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.models import HealthMetric
from app.metrics.schemas import HealthMetricCreate
from app.metrics.types import MetricType
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class MetricRegistry:
    """Centralized registry for health metric persistence.
    
    Consolidates the dual-write pattern (domain table → health_metrics)
    used across 16 domain services into a single interface.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize the registry.
        
        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db
    
    async def record_metric(
        self,
        user_id: int,
        metric_type: MetricType,
        value: float | int | None,
        measured_at: datetime,
        unit: str,
        source: str = "manual",
        meta: dict[str, Any] | None = None,
        provider_id: str | None = None,
    ) -> Optional[HealthMetric]:
        """Record a health metric to the unified store.
        
        This method consolidates the duplicate dual-write logic that was
        previously inlined in 16 domain services (exercise, food, sleep, etc.).
        
        Args:
            user_id: Owner of the metric
            metric_type: Type from MetricType enum
            value: Numeric value (None or negative skips recording)
            measured_at: UTC timestamp of measurement
            unit: Unit string (e.g., "minutes", "kcal", "bpm")
            source: Data source identifier
            meta: Optional metadata dict
            provider_id: Optional external provider ID
            
        Returns:
            HealthMetric if created, None if skipped
        """
        # Guard clauses - skip invalid values
        if value is None:
            logger.debug(f"Skipping {metric_type} - value is None")
            return None
        
        if value < 0:
            logger.debug(f"Skipping {metric_type} - negative value: {value}")
            return None
        
        # Create the health metric
        metric = HealthMetric(
            user_id=user_id,
            type=metric_type,
            value=float(value),
            unit=unit,
            measured_at=measured_at,
            source=source,
            meta=meta or {},
            provider_id=provider_id,
        )
        
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        
        logger.debug(f"Recorded {metric_type}={value} {unit} for user {user_id}")
        return metric
    
    async def record_metrics_batch(
        self,
        user_id: int,
        measured_at: datetime,
        source: str = "manual",
        metrics: list[dict] | None = None,
    ) -> list[HealthMetric]:
        """Record multiple metrics atomically.
        
        Args:
            user_id: Owner of the metrics
            measured_at: UTC timestamp for all metrics
            source: Data source identifier
            metrics: List of dicts with keys: metric_type, value, unit, meta
            
        Returns:
            List of created HealthMetric objects
        """
        if not metrics:
            return []
        
        created_metrics = []
        for metric_data in metrics:
            metric_type = metric_data.get("metric_type")
            value = metric_data.get("value")
            unit = metric_data.get("unit")
            meta = metric_data.get("meta")
            
            if value is not None and value >= 0 and metric_type:
                metric = await self.record_metric(
                    user_id=user_id,
                    metric_type=metric_type,
                    value=value,
                    measured_at=measured_at,
                    unit=unit,
                    source=source,
                    meta=meta,
                )
                if metric:
                    created_metrics.append(metric)
        
        return created_metrics