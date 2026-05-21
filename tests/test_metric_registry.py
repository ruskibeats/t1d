"""Tests for MetricRegistry - dual-write pattern consolidation."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.metric_registry import MetricRegistry
from app.metrics.types import MetricType


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def registry(mock_db):
    """Create a MetricRegistry instance."""
    return MetricRegistry(db=mock_db)


class TestMetricRegistry:
    """Test suite for MetricRegistry dual-write pattern."""

    @pytest.mark.asyncio
    async def test_record_metric_creates_health_metric(self, registry, mock_db):
        """Test that record_metric creates a HealthMetric entry."""
        # Arrange
        user_id = 1
        metric_type = MetricType.EXERCISE_MINUTES
        value = 30.0
        measured_at = datetime.now(timezone.utc)
        
        # Act
        await registry.record_metric(
            user_id=user_id,
            metric_type=metric_type,
            value=value,
            measured_at=measured_at,
            unit="minutes",
            source="manual"
        )
        
        # Assert - HealthMetric should be added
        assert mock_db.add.called
        assert mock_db.flush.called

    @pytest.mark.asyncio
    async def test_record_metric_skips_none_value(self, registry, mock_db):
        """Test that record_metric skips when value is None."""
        # Act
        await registry.record_metric(
            user_id=1,
            metric_type=MetricType.WATER,
            value=None,
            measured_at=datetime.now(),
            unit="ml"
        )
        
        # Assert - No database operations
        assert not mock_db.add.called

    @pytest.mark.asyncio
    async def test_record_metric_skips_negative_value(self, registry, mock_db):
        """Test that record_metric skips negative values."""
        # Act
        await registry.record_metric(
            user_id=1,
            metric_type=MetricType.WATER,
            value=-10.0,
            measured_at=datetime.now(),
            unit="ml"
        )
        
        # Assert - No database operations
        assert not mock_db.add.called

    @pytest.mark.asyncio
    async def test_record_metric_with_metadata(self, registry, mock_db):
        """Test that record_metric preserves metadata."""
        # Act
        await registry.record_metric(
            user_id=1,
            metric_type=MetricType.BODY_BATTERY_CHANGE,
            value=5,
            measured_at=datetime.now(),
            unit="score_delta",
            meta={"value": 75, "charged": True}
        )
        
        # Assert - Metadata was passed through
        call_args = mock_db.add.call_args[0][0]
        assert call_args.meta == {"value": 75, "charged": True}

    @pytest.mark.asyncio
    async def test_record_multiple_metrics_batch(self, registry, mock_db):
        """Test recording multiple metrics atomically."""
        # Act
        await registry.record_metrics_batch(
            user_id=1,
            measured_at=datetime.now(),
            metrics=[
                {"metric_type": MetricType.CALORIES, "value": 200, "unit": "kcal"},
                {"metric_type": MetricType.PROTEIN, "value": 15, "unit": "g"},
                {"metric_type": MetricType.CARBS, "value": 30, "unit": "g"},
            ]
        )
        
        # Assert - All metrics were recorded
        assert mock_db.flush.call_count >= 1

    @pytest.mark.asyncio
    async def test_unit_validation(self, registry, mock_db):
        """Test that common units are accepted."""
        valid_units = [
            ("minutes", MetricType.EXERCISE_MINUTES),
            ("kcal", MetricType.CALORIES),
            ("g", MetricType.PROTEIN),
            ("bpm", MetricType.HEART_RATE),
            ("kg", MetricType.WEIGHT),
            ("hours", MetricType.SLEEP_HOURS),
            ("%", MetricType.SPO2),
        ]
        
        for unit, metric_type in valid_units:
            mock_db.reset_mock()
            await registry.record_metric(
                user_id=1,
                metric_type=metric_type,
                value=10.0,
                measured_at=datetime.now(),
                unit=unit
            )
            assert mock_db.add.called, f"Failed for unit {unit}"