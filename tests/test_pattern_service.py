"""Comprehensive unit tests for PatternService.

Tests cover:
- Time-in-range (TIR) calculations
- Post-meal spike detection
- Overnight hypoglycemia detection
- Exercise impact analysis
- Delayed high-fat meal effects
- Correlation analysis
- Edge cases and boundary conditions
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from app.db.models import GlucoseReading, ContextEvent


# =============================================================================
# calculate_time_in_range() Tests
# =============================================================================

class TestCalculateTimeInRange:
    """Tests for calculate_time_in_range method."""
    
    @pytest.mark.asyncio
    async def test_tir_empty_readings(self, db_session, test_user, pattern_service):
        """No readings → returns zeros/N/A."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["readings"]["total"] == 0
        assert result["time_in_range"]["percentage"] == 0
        assert result["grade"] == "N/A"
    
    @pytest.mark.asyncio
    async def test_tir_all_in_range(self, db_session, test_user, pattern_service):
        """All readings 70-180 → 100% TIR, grade A."""
        readings = []
        for i in range(10):
            readings.append(GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0 + i * 5,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ))
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["percentage"] == 100.0
        assert result["grade"] == "A"
    
    @pytest.mark.asyncio
    async def test_tir_all_below_range(self, db_session, test_user, pattern_service):
        """All readings < 70 → 0% TIR, 100% TBR."""
        readings = []
        for i in range(10):
            readings.append(GlucoseReading(
                user_id=test_user.id,
                glucose_value=50.0 + i * 2,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ))
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["percentage"] == 0
        assert result["time_in_range"]["below_range"]["percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_tir_all_above_range(self, db_session, test_user, pattern_service):
        """All readings > 180 → 0% TIR, 100% TAR."""
        readings = []
        for i in range(10):
            readings.append(GlucoseReading(
                user_id=test_user.id,
                glucose_value=200.0 + i * 5,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ))
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["percentage"] == 0
        assert result["time_in_range"]["above_range"]["percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_tir_mixed_readings(self, db_session, test_user, pattern_service):
        """Realistic mix → correct percentages."""
        # 40 below, 60 in range, 30 above = 100 total, 60% TIR
        values = [50, 55, 65, 100, 120, 140, 150, 170, 180, 200]
        readings = []
        for i, v in enumerate(values):
            readings.append(GlucoseReading(
                user_id=test_user.id,
                glucose_value=float(v),
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ))
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["readings"]["total"] == 10
        assert result["time_in_range"]["percentage"] == 60.0
        assert result["time_in_range"]["below_range"]["percentage"] == 30.0
        assert result["time_in_range"]["above_range"]["percentage"] == 10.0
    
    @pytest.mark.asyncio
    async def test_tir_boundary_values(self, db_session, test_user, pattern_service):
        """Readings at exactly 70 and 180 → counted as in-range."""
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=70.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ),
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=180.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ),
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["percentage"] == 100.0
    
    @pytest.mark.asyncio
    async def test_tir_severe_thresholds(self, db_session, test_user, pattern_service):
        """Readings at 54 and 250 → severe counts correct."""
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=54.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ),
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=250.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ),
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["below_range"]["severe_count"] == 1
        assert result["time_in_range"]["above_range"]["severe_count"] == 1
    
    @pytest.mark.asyncio
    async def test_tir_estimated_a1c(self, db_session, test_user, pattern_service):
        """Verify A1C formula: (avg + 46.7) / 28.7."""
        avg = 150.0  # Expected A1C = (150 + 46.7) / 28.7 = 6.8
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=float(avg),
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            for i in range(10)
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        expected_a1c = round((avg + 46.7) / 28.7, 1)
        assert result["estimated_a1c"] == expected_a1c
    
    @pytest.mark.asyncio
    async def test_tir_grade_calculation(self, db_session, test_user, pattern_service):
        """TIR ≥ 70% + TBR < 4% → grade A."""
        # 70 in range, 3 below, 7 above = 100 total
        values = [100] * 70 + [60] * 3 + [200] * 7
        readings = []
        for i, v in enumerate(values):
            readings.append(GlucoseReading(
                user_id=test_user.id,
                glucose_value=float(v),
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            ))
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["grade"] == "A"
    
    @pytest.mark.asyncio
    async def test_tir_coefficient_of_variation(self, db_session, test_user, pattern_service):
        """Verify CV calculation."""
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=float(v),
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            for i, v in enumerate([100, 110, 90, 105, 95])
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        # CV = std_dev / mean * 100
        assert "coefficient_of_variation" in result["readings"]
        assert result["readings"]["coefficient_of_variation"] > 0
    
    @pytest.mark.asyncio
    async def test_tir_single_reading(self, db_session, test_user, pattern_service):
        """One reading → std_dev = 0."""
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=100.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["readings"]["std_dev"] == 0
    
    @pytest.mark.asyncio
    async def test_tir_readings_at_exact_hypo_threshold(self, db_session, test_user, pattern_service):
        """Value = 70 → NOT below range."""
        readings = [
            GlucoseReading(
                user_id=test_user.id,
                glucose_value=70.0,
                glucose_units="mg/dL",
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor",
                source="dexcom",
                trend="flat",
            )
            for i in range(5)
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=1)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.calculate_time_in_range(
            db_session, test_user.id, start, end
        )
        
        assert result["time_in_range"]["below_range"]["count"] == 0
        assert result["time_in_range"]["percentage"] == 100.0


# =============================================================================
# detect_post_meal_spikes() Tests
# =============================================================================

class TestDetectPostMealSpikes:
    """Tests for detect_post_meal_spikes method."""
    
    @pytest.mark.asyncio
    async def test_spikes_no_meals(self, db_session, test_user, pattern_service):
        """No meal events → empty list."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_spikes_meal_no_glucose(self, db_session, test_user, pattern_service):
        """Meal with no nearby glucose → no spikes."""
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Test Meal", carbs_grams=50,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(meal)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_spikes_meal_with_spike(self, db_session, test_user, pattern_service):
        """Meal followed by > 50 mg/dL rise → 1 spike detected."""
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Test Meal", carbs_grams=50,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        db_session.add(meal)
        await db_session.commit()
        
        # Pre-meal reading
        pre = GlucoseReading(
            user_id=test_user.id, glucose_value=100.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3, minutes=15),
            reading_type="sensor", source="dexcom", trend="flat",
        )
        # Post-meal spike
        post = GlucoseReading(
            user_id=test_user.id, glucose_value=181.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
            reading_type="sensor", source="dexcom", trend="flat",
        )
        db_session.add(pre)
        db_session.add(post)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["glucose_rise"] >= 50
    
    @pytest.mark.asyncio
    async def test_spikes_meal_no_spike(self, db_session, test_user, pattern_service):
        """Meal with flat glucose → no spikes."""
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Test Meal", carbs_grams=50,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(meal)
        await db_session.commit()
        
        readings = [
            GlucoseReading(
                user_id=test_user.id, glucose_value=100.0,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
                reading_type="sensor", source="dexcom", trend="flat",
            ),
            GlucoseReading(
                user_id=test_user.id, glucose_value=102.0,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
                reading_type="sensor", source="dexcom", trend="flat",
            ),
        ]
        for r in readings:
            db_session.add(r)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_spikes_multiple_meals(self, db_session, test_user, pattern_service):
        """3 meals, 2 with spikes → 2 spikes."""
        meal_hours = [6, 3, 1]
        meals = [
            ContextEvent(user_id=test_user.id, event_type="meal", description=f"Meal {i}", carbs_grams=50,
                        timestamp=datetime.now(timezone.utc) - timedelta(hours=meal_hours[i]))
            for i in range(3)
        ]
        for m in meals:
            db_session.add(m)
        
        # First meal - spike
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=100.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=6, minutes=15), reading_type="sensor", source="dexcom", trend="flat"))
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=181.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=5), reading_type="sensor", source="dexcom", trend="flat"))
        
        # Second meal - spike
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=100.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3, minutes=15), reading_type="sensor", source="dexcom", trend="flat"))
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=181.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2), reading_type="sensor", source="dexcom", trend="flat"))
        
        # Third meal - no spike
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=100.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=1), reading_type="sensor", source="dexcom", trend="flat"))
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=105.0,
            timestamp=datetime.now(timezone.utc), reading_type="sensor", source="dexcom", trend="flat"))
        
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_spikes_min_carbs_filter(self, db_session, test_user, pattern_service):
        """Meal with 20g carbs, min_carbs=30 → filtered out."""
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Snack", carbs_grams=20,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        db_session.add(meal)
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end, min_carbs=30
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_spikes_severity_classification(self, db_session, test_user, pattern_service):
        """Rise of 120 mg/dL → 'severe'."""
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="High Carb Meal", carbs_grams=100,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3),
        )
        db_session.add(meal)
        await db_session.commit()
        
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=100.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=3, minutes=15), reading_type="sensor", source="dexcom", trend="flat"))
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=220.0,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2), reading_type="sensor", source="dexcom", trend="flat"))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["severity"] == "severe"
    
    @pytest.mark.asyncio
    async def test_spikes_time_to_peak(self, db_session, test_user, pattern_service):
        """Verify peak time calculation."""
        meal_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        meal = ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Test Meal", carbs_grams=50,
            timestamp=meal_ts,
        )
        db_session.add(meal)
        await db_session.commit()
        
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=100.0,
            timestamp=meal_ts - timedelta(minutes=15), reading_type="sensor", source="dexcom", trend="flat"))
        db_session.add(GlucoseReading(user_id=test_user.id, glucose_value=181.0,
            timestamp=meal_ts + timedelta(minutes=30), reading_type="sensor", source="dexcom", trend="flat"))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_post_meal_spikes(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["time_to_peak_minutes"] == 30


# =============================================================================
# detect_overnight_hypoglycemia() Tests
# =============================================================================

class TestDetectOvernightHypoglycemia:
    """Tests for detect_overnight_hypoglycemia method."""
    
    @pytest.mark.asyncio
    async def test_overnight_no_lows(self, db_session, test_user, pattern_service):
        """All readings > 70 → empty list."""
        base = (datetime.now(timezone.utc) - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(22, 6+24):  # Night hours
            for minute in range(0, 60, 15):
                db_session.add(GlucoseReading(
                    user_id=test_user.id, glucose_value=100.0,
                    timestamp=base + timedelta(hours=hour, minutes=minute),
                    reading_type="sensor", source="dexcom", trend="flat",
                ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_overnight_hypoglycemia(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_overnight_single_low(self, db_session, test_user, pattern_service):
        """One night with reading at 65 → 1 event."""
        base = (datetime.now(timezone.utc) - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(22, 6+24):
            for minute in range(0, 60, 15):
                val = 65.0 if hour == 27 and minute == 0 else 100.0
                db_session.add(GlucoseReading(
                    user_id=test_user.id, glucose_value=val,
                    timestamp=base + timedelta(hours=hour, minutes=minute),
                    reading_type="sensor", source="dexcom", trend="flat",
                ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_overnight_hypoglycemia(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["lowest_value"] == 65.0
    
    @pytest.mark.asyncio
    async def test_overnight_multiple_nights(self, db_session, test_user, pattern_service):
        """3 nights, 2 with lows → 2 events."""
        for day_offset in range(3):
            base = (datetime.now(timezone.utc) - timedelta(days=day_offset+1)).replace(hour=0, minute=0, second=0, microsecond=0)
            for hour in range(22, 6+24):
                for minute in range(0, 60, 30):
                    # Day 1 and Day 3 have lows
                    val = 65.0 if (day_offset in [0, 2] and hour == 27) else 100.0
                    db_session.add(GlucoseReading(
                        user_id=test_user.id, glucose_value=val,
                        timestamp=base + timedelta(hours=hour, minutes=minute),
                        reading_type="sensor", source="dexcom", trend="flat",
                    ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_overnight_hypoglycemia(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 2
    
    @pytest.mark.asyncio
    async def test_overnight_severe_low(self, db_session, test_user, pattern_service):
        """Reading at 50 → severity 'severe'."""
        base = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        for hour in range(22, 6+24):
            for minute in range(0, 60, 30):
                val = 50.0 if hour == 27 else 100.0
                db_session.add(GlucoseReading(
                    user_id=test_user.id, glucose_value=val,
                    timestamp=base + timedelta(hours=hour, minutes=minute),
                    reading_type="sensor", source="dexcom", trend="flat",
                ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_overnight_hypoglycemia(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["severity"] == "severe"
    
    @pytest.mark.asyncio
    async def test_overnight_time_window(self, db_session, test_user, pattern_service):
        """Low at 3 AM → detected; low at 2 PM → not detected."""
        base = (datetime.now(timezone.utc) - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        # Night time low
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=65.0,
            timestamp=base + timedelta(hours=27),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        # Day time low (should not be detected)
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=65.0,
            timestamp=base.replace(hour=14, minute=0),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        # Normal night readings
        for hour in range(22, 6+24):
            if hour != 27:
                db_session.add(GlucoseReading(
                    user_id=test_user.id, glucose_value=100.0,
                    timestamp=base + timedelta(hours=hour),
                    reading_type="sensor", source="dexcom", trend="flat",
                ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_overnight_hypoglycemia(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["lowest_time"].hour == 3


# =============================================================================
# analyze_exercise_impact() Tests
# =============================================================================

class TestAnalyzeExerciseImpact:
    """Tests for analyze_exercise_impact method."""
    
    @pytest.mark.asyncio
    async def test_exercise_no_events(self, db_session, test_user, pattern_service):
        """No exercise → empty list."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_exercise_impact(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_exercise_with_drop(self, db_session, test_user, pattern_service):
        """Exercise followed by glucose drop → impact detected."""
        ex_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="moderate", duration=45, heart_rate_avg=140,
            timestamp=ex_ts,
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=150.0,
            timestamp=ex_ts - timedelta(hours=2),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=130.0,
            timestamp=ex_ts + timedelta(hours=1),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_exercise_impact(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["impact"]["type"] == "moderate_drop"
    
    @pytest.mark.asyncio
    async def test_exercise_hypo_risk(self, db_session, test_user, pattern_service):
        """Exercise with post-glucose < 70 → hypo_risk flagged."""
        ex_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="high", duration=30, heart_rate_avg=165,
            timestamp=ex_ts,
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=120.0,
            timestamp=ex_ts - timedelta(hours=1),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=60.0,
            timestamp=ex_ts + timedelta(hours=1),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_exercise_impact(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
        assert result[0]["impact"]["hypoglycemia_risk"] == True
    
    @pytest.mark.asyncio
    async def test_exercise_no_glucose_data(self, db_session, test_user, pattern_service):
        """Exercise with no nearby readings → skipped."""
        ex_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="moderate", duration=45,
            timestamp=ex_ts,
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_exercise_impact(
            db_session, test_user.id, start, end
        )
        
        assert result == []


# =============================================================================
# detect_delayed_high_fat_effects() Tests
# =============================================================================

class TestDetectDelayedHighFatEffects:
    """Tests for detect_delayed_high_fat_effects method."""
    
    @pytest.mark.asyncio
    async def test_delayed_fat_no_meals(self, db_session, test_user, pattern_service):
        """No high-fat meals → empty list."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_delayed_high_fat_effects(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_delayed_fat_with_rise(self, db_session, test_user, pattern_service):
        """High-fat meal + delayed spike → detected."""
        meal_ts = datetime.now(timezone.utc) - timedelta(hours=6)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Pizza", carbs_grams=80, fat_grams=35,
            timestamp=meal_ts,
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=100.0,
            timestamp=meal_ts,
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=181.0,
            timestamp=meal_ts + timedelta(hours=5),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_delayed_high_fat_effects(
            db_session, test_user.id, start, end
        )
        
        assert len(result) == 1
    
    @pytest.mark.asyncio
    async def test_delayed_fat_threshold(self, db_session, test_user, pattern_service):
        """Meal with 20g fat, threshold 25g → filtered out."""
        meal_ts = datetime.now(timezone.utc) - timedelta(hours=6)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Snack", carbs_grams=30, fat_grams=20,
            timestamp=meal_ts,
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.detect_delayed_high_fat_effects(
            db_session, test_user.id, start, end, fat_threshold=25
        )
        
        assert result == []


# =============================================================================
# analyze_correlations() Tests
# =============================================================================

class TestAnalyzeCorrelations:
    """Tests for analyze_correlations method."""
    
    @pytest.mark.asyncio
    async def test_correlations_no_events(self, db_session, test_user, pattern_service):
        """No events → empty list."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_correlations(
            db_session, test_user.id, start, end
        )
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_correlations_meal_spike_correlation(self, db_session, test_user, pattern_service):
        """Meals with spikes → correlation > 0."""
        meal_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Meal", carbs_grams=50,
            timestamp=meal_ts,
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=100.0,
            timestamp=meal_ts,
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=200.0,
            timestamp=meal_ts + timedelta(hours=1),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_correlations(
            db_session, test_user.id, start, end
        )
        
        assert len(result) > 0
        assert result[0].event_type == "meal"
        assert result[0].correlation_strength > 0
    
    @pytest.mark.asyncio
    async def test_correlations_exercise_drop_correlation(self, db_session, test_user, pattern_service):
        """Exercise with drops → correlation > 0."""
        ex_ts = datetime.now(timezone.utc) - timedelta(hours=3)
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="moderate", duration=45,
            timestamp=ex_ts,
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=150.0,
            timestamp=ex_ts,
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        db_session.add(GlucoseReading(
            user_id=test_user.id, glucose_value=60.0,
            timestamp=ex_ts + timedelta(hours=1),
            reading_type="sensor", source="dexcom", trend="flat",
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.analyze_correlations(
            db_session, test_user.id, start, end
        )
        
        assert len(result) > 0
        assert result[0].event_type == "exercise"


# =============================================================================
# generate_statistical_summary() Tests
# =============================================================================

class TestGenerateStatisticalSummary:
    """Tests for generate_statistical_summary method."""
    
    @pytest.mark.asyncio
    async def test_statistical_summary_full(self, db_session, test_user, pattern_service):
        """Complete dataset → all sections present."""
        # Add some glucose readings
        for i in range(10):
            db_session.add(GlucoseReading(
                user_id=test_user.id, glucose_value=100.0 + i,
                timestamp=datetime.now(timezone.utc) - timedelta(hours=i),
                reading_type="sensor", source="dexcom", trend="flat",
            ))
        # Add a meal
        db_session.add(ContextEvent(
            user_id=test_user.id, event_type="meal",
            description="Meal", carbs_grams=50,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        ))
        await db_session.commit()
        
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.generate_statistical_summary(
            db_session, test_user.id, start, end, period="weekly"
        )
        
        assert "tir_analysis" in result
        assert "post_meal_spikes" in result
        assert "overnight_hypoglycemia" in result
        assert "exercise_impact" in result
        assert "correlations" in result
    
    @pytest.mark.asyncio
    async def test_statistical_summary_empty(self, db_session, test_user, pattern_service):
        """No data → graceful empty result."""
        start = datetime.now(timezone.utc) - timedelta(days=7)
        end = datetime.now(timezone.utc)
        
        result = await pattern_service.generate_statistical_summary(
            db_session, test_user.id, start, end, period="weekly"
        )
        
        assert result["tir_analysis"]["readings"]["total"] == 0
        assert result["post_meal_spikes"]["count"] == 0
        assert result["overnight_hypoglycemia"]["event_count"] == 0