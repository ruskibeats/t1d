---
name: phase2-pattern-tests
description: Writes comprehensive unit tests for the T1D Companion PatternService. Covers TIR calculation, spike detection, overnight hypoglycemia, exercise impact, and edge cases. Use when implementing Phase 2 pattern service tests.
model: poolside/laguna-xs.2:free
context: fork
---

# Phase 2: Pattern Service Unit Tests

## Task

Write `tests/test_pattern_service.py` — comprehensive unit tests for `app/services/pattern_service.py`. The `PatternService` is already fully implemented. You're writing tests against existing code.

## Files to Create

- `tests/test_pattern_service.py` — the test file (uses fixtures from `tests/conftest.py`)

## What to Test

The `PatternService` has these public methods:
1. `calculate_time_in_range(session, user_id, start_date, end_date)`
2. `detect_post_meal_spikes(session, user_id, start_date, end_date, min_carbs, spike_threshold)`
3. `detect_overnight_hypoglycemia(session, user_id, start_date, end_date)`
4. `analyze_exercise_impact(session, user_id, start_date, end_date)`
5. `detect_delayed_high_fat_effects(session, user_id, start_date, end_date, fat_threshold, delay_hours)`
6. `analyze_correlations(session, user_id, start_date, end_date)`
7. `generate_statistical_summary(session, user_id, start_date, end_date, period)`

## Test Infrastructure

Reuse the `db_session` and `test_user` fixtures from `conftest.py`. Create additional fixtures:

```python
@pytest_asyncio.fixture
async def pattern_service():
    from app.services.pattern_service import PatternService
    return PatternService()

@pytest_asyncio.fixture
async def glucose_dataset(db_session, test_user):
    """Create a realistic glucose dataset spanning 7 days."""
    from app.db.models import GlucoseReading
    from datetime import datetime, timedelta, timezone
    import random
    random.seed(42)
    
    readings = []
    base = datetime.now(timezone.utc) - timedelta(days=7)
    
    for day in range(7):
        for hour in range(24):
            for minute in range(0, 60, 5):  # Every 5 minutes
                # Simulate realistic glucose curve
                base_val = 120
                # Morning rise (dawn phenomenon)
                if 4 <= hour <= 7:
                    base_val += 30 + (hour - 4) * 10
                # Post-meal spikes
                if hour in [8, 13, 19] and minute < 30:
                    base_val += 60
                # Overnight low
                if 2 <= hour <= 4:
                    base_val -= 40
                
                value = base_val + random.randint(-15, 15)
                value = max(40, min(350, value))
                
                reading = GlucoseReading(
                    user_id=test_user.id,
                    glucose_value=float(value),
                    glucose_units="mg/dL",
                    timestamp=base + timedelta(days=day, hours=hour, minutes=minute),
                    reading_type="sensor",
                    source="dexcom",
                    trend="flat",
                )
                readings.append(reading)
    
    for r in readings:
        db_session.add(r)
    await db_session.commit()
    return readings

@pytest_asyncio.fixture
async def meal_events(db_session, test_user):
    """Create meal events for spike detection testing."""
    from app.db.models import ContextEvent
    from datetime import datetime, timedelta, timezone
    
    meals = [
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="breakfast",
            description="Oatmeal", carbs_grams=45,
            timestamp=datetime.now(timezone.utc) - timedelta(days=3, hours=8),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="lunch",
            description="Sandwich", carbs_grams=55,
            timestamp=datetime.now(timezone.utc) - timedelta(days=3, hours=13),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="dinner",
            description="Pasta", carbs_grams=75,
            timestamp=datetime.now(timezone.utc) - timedelta(days=3, hours=19),
        ),
        # High-fat meal for delayed effect testing
        ContextEvent(
            user_id=test_user.id, event_type="meal", event_subtype="dinner",
            description="Pizza", carbs_grams=80, fat_grams=35, protein_grams=30, calories=850,
            timestamp=datetime.now(timezone.utc) - timedelta(days=2, hours=20),
        ),
    ]
    for m in meals:
        db_session.add(m)
    await db_session.commit()
    return meals

@pytest_asyncio.fixture
async def exercise_events(db_session, test_user):
    """Create exercise events for impact testing."""
    from app.db.models import ContextEvent
    from datetime import datetime, timedelta, timezone
    
    exercises = [
        ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="moderate", duration=45, heart_rate_avg=140,
            timestamp=datetime.now(timezone.utc) - timedelta(days=2, hours=17),
        ),
        ContextEvent(
            user_id=test_user.id, event_type="exercise",
            intensity="high", duration=30, heart_rate_avg=165,
            timestamp=datetime.now(timezone.utc) - timedelta(days=1, hours=7),
        ),
    ]
    for e in exercises:
        db_session.add(e)
    await db_session.commit()
    return exercises
```

## Required Tests

### calculate_time_in_range()

1. **`test_tir_empty_readings`** — no readings → returns zeros/N/A
2. **`test_tir_all_in_range`** — all readings 70-180 → 100% TIR, grade A
3. **`test_tir_all_below_range`** — all readings < 70 → 0% TIR, 100% TBR
4. **`test_tir_all_above_range`** — all readings > 180 → 0% TIR, 100% TAR
5. **`test_tir_mixed_readings`** — realistic mix → correct percentages
6. **`test_tir_boundary_values`** — readings at exactly 70 and 180 → counted as in-range
7. **`test_tir_severe_thresholds`** — readings at 54 and 250 → severe counts correct
8. **`test_tir_estimated_a1c`** — verify A1C formula: (avg + 46.7) / 28.7
9. **`test_tir_grade_calculation`** — TIR ≥ 70% + TBR < 4% → grade A
10. **`test_tir_coefficient_of_variation`** — verify CV calculation
11. **`test_tir_single_reading`** — one reading → std_dev = 0
12. **`test_tir_readings_at_exact_hypo_threshold`** — value = 70 → NOT below range

### detect_post_meal_spikes()

13. **`test_spikes_no_meals`** — no meal events → empty list
14. **`test_spikes_meal_no_glucose`** — meal with no nearby glucose → no spikes
15. **`test_spikes_meal_with_spike`** — meal followed by > 50 mg/dL rise → 1 spike detected
16. **`test_spikes_meal_no_spike`** — meal with flat glucose → no spikes
17. **`test_spikes_multiple_meals`** — 3 meals, 2 with spikes → 2 spikes
18. **`test_spikes_min_carbs_filter`** — meal with 20g carbs, min_carbs=30 → filtered out
19. **`test_spikes_severity_classification`** — rise of 120 mg/dL → "severe"
20. **`test_spikes_time_to_peak`** — verify peak time calculation

### detect_overnight_hypoglycemia()

21. **`test_overnight_no_lows`** — all readings > 70 → empty list
22. **`test_overnight_single_low`** — one night with reading at 65 → 1 event
23. **`test_overnight_multiple_nights`** — 3 nights, 2 with lows → 2 events
24. **`test_overnight_severe_low`** — reading at 50 → severity "severe"
25. **`test_overnight_time_window`** — low at 3 AM → detected; low at 2 PM → not detected

### analyze_exercise_impact()

26. **`test_exercise_no_events`** — no exercise → empty list
27. **`test_exercise_with_drop`** — exercise followed by glucose drop → impact detected
28. **`test_exercise_hypo_risk`** — exercise with post-glucose < 70 → hypo_risk flagged
29. **`test_exercise_no_glucose_data`** — exercise with no nearby readings → skipped

### detect_delayed_high_fat_effects()

30. **`test_delayed_fat_no_meals`** — no high-fat meals → empty list
31. **`test_delayed_fat_with_rise`** — high-fat meal + delayed spike → detected
32. **`test_delayed_fat_threshold`** — meal with 20g fat, threshold 25g → filtered out

### analyze_correlations()

33. **`test_correlations_no_events`** — no events → empty list
34. **`test_correlations_meal_spike_correlation`** — meals with spikes → correlation > 0
35. **`test_correlations_exercise_drop_correlation`** — exercise with drops → correlation > 0

### generate_statistical_summary()

36. **`test_statistical_summary_full`** — complete dataset → all sections present
37. **`test_statistical_summary_empty`** — no data → graceful empty result

## Critical Rules

1. **Only create `tests/test_pattern_service.py`** — don't modify any source files
2. **Use the `db_session` and `test_user` fixtures from conftest.py**
3. **Each test is independent** — no shared state between tests
4. **Test edge cases aggressively** — empty data, boundary values, single items
5. **Minimum 37 tests** — the list above is the floor
6. **All tests must pass with `pytest tests/test_pattern_service.py -x -v`**

## Verification

After writing, verify:
- [ ] At least 37 test functions
- [ ] All use `@pytest.mark.asyncio`
- [ ] All use proper fixtures
- [ ] Tests cover all 7 PatternService methods
- [ ] Edge cases covered: empty data, boundaries, single items
- [ ] `pytest tests/test_pattern_service.py -x -v` passes

## Output

Write your implementation notes to: `PHASE2_W5_PATTERN_TESTS.md`
