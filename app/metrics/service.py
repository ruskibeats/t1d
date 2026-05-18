"""Health metric service — CRUD, queries, batch ingest, daily aggregation."""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import and_, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.models import HealthDailyAggregate, HealthMetric
from app.metrics.schemas import (
    BatchHealthMetricCreate,
    HealthMetricCreate,
    HealthMetricQuery,
    HealthMetricSummary,
)
from app.metrics.types import MetricType


class HealthMetricService:
    """Service for health metric CRUD and queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: int, data: HealthMetricCreate) -> HealthMetric:
        metric = HealthMetric(
            user_id=user_id,
            type=data.type,
            value=data.value,
            unit=data.unit,
            measured_at=data.measured_at,
            ended_at=data.ended_at,
            source=data.source,
            provider_id=data.provider_id,
            event_group_id=data.event_group_id,
            meta=data.meta,
            event_group_id=data.event_group_id,
        )
        self.db.add(metric)
        await self.db.flush()
        await self.db.refresh(metric)
        return metric

    async def create_batch(self, user_id: int, data: BatchHealthMetricCreate) -> tuple[list[HealthMetric], int]:
        skipped = 0
        created = []
        for item in data.metrics:
            source = item.source or data.source or "manual"
            if item.provider_id:
                existing = await self.db.execute(
                    select(HealthMetric).where(
                        and_(
                            HealthMetric.user_id == user_id,
                            HealthMetric.type == item.type,
                            HealthMetric.source == source,
                            HealthMetric.provider_id == item.provider_id,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    skipped += 1
                    continue

            metric = HealthMetric(
                user_id=user_id,
                type=item.type,
                value=item.value,
                unit=item.unit,
                measured_at=item.measured_at,
                ended_at=item.ended_at,
                source=source,
                provider_id=item.provider_id,
                meta=item.meta,
                event_group_id=item.event_group_id,
            )
            self.db.add(metric)
            created.append(metric)

        await self.db.flush()
        for metric in created:
            await self.db.refresh(metric)
        return created, skipped

    async def get_by_id(self, user_id: int, metric_id: int) -> Optional[HealthMetric]:
        result = await self.db.execute(
            select(HealthMetric).where(
                HealthMetric.user_id == user_id,
                HealthMetric.id == metric_id,
            )
        )
        return result.scalar_one_or_none()

    async def query(self, user_id: int, params: HealthMetricQuery) -> list[HealthMetric]:
        stmt = (
            select(HealthMetric)
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.measured_at >= params.start_time,
                HealthMetric.measured_at <= params.end_time,
            )
            .order_by(desc(HealthMetric.measured_at))
            .offset(params.offset)
            .limit(params.limit)
        )
        if params.types:
            stmt = stmt.where(HealthMetric.type.in_(params.types))
        if params.sources:
            stmt = stmt.where(HealthMetric.source.in_(params.sources))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count(self, user_id: int, params: HealthMetricQuery) -> int:
        stmt = select(func.count(HealthMetric.id)).where(
            HealthMetric.user_id == user_id,
            HealthMetric.measured_at >= params.start_time,
            HealthMetric.measured_at <= params.end_time,
        )
        if params.types:
            stmt = stmt.where(HealthMetric.type.in_(params.types))
        if params.sources:
            stmt = stmt.where(HealthMetric.source.in_(params.sources))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_summary(self, user_id: int, metric_type: MetricType, start_time: datetime, end_time: datetime) -> HealthMetricSummary:
        result = await self.db.execute(
            select(
                func.count(HealthMetric.id).label("count"),
                func.avg(HealthMetric.value).label("avg"),
                func.min(HealthMetric.value).label("min"),
                func.max(HealthMetric.value).label("max"),
                func.sum(HealthMetric.value).label("sum"),
                func.min(HealthMetric.measured_at).label("first"),
                func.max(HealthMetric.measured_at).label("last"),
            ).where(
                HealthMetric.user_id == user_id,
                HealthMetric.type == metric_type,
                HealthMetric.measured_at >= start_time,
                HealthMetric.measured_at <= end_time,
            )
        )
        row = result.one()
        return HealthMetricSummary(
            type=metric_type,
            count=row.count,
            avg=row.avg,
            min=row.min,
            max=row.max,
            sum=row.sum,
            first=row.first,
            last=row.last,
        )

    async def get_recent(self, user_id: int, metric_types: list[MetricType], hours: int = 24) -> dict[MetricType, list[HealthMetric]]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        results: dict[MetricType, list[HealthMetric]] = defaultdict(list)
        for mt in metric_types:
            result = await self.db.execute(
                select(HealthMetric)
                .where(
                    HealthMetric.user_id == user_id,
                    HealthMetric.type == mt,
                    HealthMetric.measured_at >= cutoff,
                )
                .order_by(desc(HealthMetric.measured_at))
                .limit(20)
            )
            results[mt] = list(result.scalars().all())
        return results

    async def delete(self, user_id: int, metric_id: int) -> bool:
        result = await self.db.execute(
            select(HealthMetric).where(
                HealthMetric.user_id == user_id,
                HealthMetric.id == metric_id,
            )
        )
        metric = result.scalar_one_or_none()
        if not metric:
            return False
        await self.db.delete(metric)
        await self.db.flush()
        return True


class HealthAggregateService:
    """Service for daily aggregate computation and queries."""

    AGGREGATION_FUNCTIONS: dict[MetricType, str] = {
        MetricType.BLOOD_GLUCOSE: "avg",
        MetricType.INSULIN: "sum",
        MetricType.STEPS: "sum",
        MetricType.CARBS: "sum",
        MetricType.CALORIES: "sum",
        MetricType.EXERCISE_MINUTES: "sum",
        MetricType.SLEEP_HOURS: "sum",
        MetricType.SLEEP_SCORE: "avg",
        MetricType.WEIGHT: "last",
        MetricType.WATER: "sum",
        MetricType.MOOD_SCORE: "avg",
        MetricType.HEART_RATE_VARIABILITY: "avg",
        MetricType.SPO2: "avg",
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_day(self, user_id: int, metric_type: MetricType, local_date: datetime) -> Optional[HealthDailyAggregate]:
        start = local_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)

        result = await self.db.execute(
            select(
                func.count(HealthMetric.id).label("count"),
                func.avg(HealthMetric.value).label("avg"),
                func.min(HealthMetric.value).label("min"),
                func.max(HealthMetric.value).label("max"),
                func.sum(HealthMetric.value).label("sum"),
                func.max(HealthMetric.measured_at).label("last_at"),
            ).where(
                HealthMetric.user_id == user_id,
                HealthMetric.type == metric_type,
                HealthMetric.measured_at >= start,
                HealthMetric.measured_at < end,
            )
        )
        row = result.one()
        if row.count == 0:
            return None

        last_value = None
        if row.last_at:
            last_result = await self.db.execute(
                select(HealthMetric.value)
                .where(
                    HealthMetric.user_id == user_id,
                    HealthMetric.type == metric_type,
                    HealthMetric.measured_at == row.last_at,
                )
                .limit(1)
            )
            last_value = last_result.scalar_one_or_none()

        source_result = await self.db.execute(
            select(HealthMetric.source)
            .where(
                HealthMetric.user_id == user_id,
                HealthMetric.type == metric_type,
                HealthMetric.measured_at >= start,
                HealthMetric.measured_at < end,
            )
            .group_by(HealthMetric.source)
            .order_by(func.count(HealthMetric.id).desc())
            .limit(1)
        )
        primary_source = source_result.scalar_one_or_none()

        conflict_keys = {"user_id": user_id, "type": metric_type, "local_date": start}
        values = {
            "value_sum": row.sum,
            "value_avg": row.avg,
            "value_min": row.min,
            "value_max": row.max,
            "value_last": last_value,
            "value_count": row.count,
            "source_primary": primary_source,
            "aggregation_version": 1,
        }

        stmt = (
            pg_insert(HealthDailyAggregate)
            .values(**{**conflict_keys, **values})
            .on_conflict_do_update(
                index_elements=["user_id", "type", "local_date"],
                set_=values,
            )
        )
        await self.db.execute(stmt)
        await self.db.flush()

        result = await self.db.execute(
            select(HealthDailyAggregate).where(
                HealthDailyAggregate.user_id == user_id,
                HealthDailyAggregate.type == metric_type,
                HealthDailyAggregate.local_date == start,
            )
        )
        return result.scalar_one_or_none()
