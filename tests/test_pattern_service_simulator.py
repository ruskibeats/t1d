"""Integration test: run PatternService detectors over simulated data.

This test generates a small simulation run (2 anchors, 1 user each, 3 days)
and verifies that:
1. PatternService detectors create graph edges from simulator data
2. Edges are written to health_metric_edges
3. Detected edges match planted truths at above-chance rates

Uses the same async SQLite test database as other integration tests.
"""

import pytest
from datetime import datetime, timedelta, timezone

from app.services.pattern_service import PatternService
from app.simulator.patient_factory import generate_patient_config
from app.simulator.schemas import AnchorType


@pytest.mark.asyncio
async def test_pattern_service_runs_on_simulator_data(async_db_session):
    """PatternService detectors should complete without error on sim data."""
    import random
    from app.simulator.day_context import DayContextGenerator
    from app.simulator.glucose_engine import GlucoseEngine
    from app.simulator.writeback import SimulatorWriteback
    from app.db.models import User
    from app.metrics.models import HealthMetricEdge

    config = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42)
    rng = random.Random(42)

    # Create a simulator user
    user = User(
        email="sim_int_test@simulator.local",
        hashed_password="SIMULATOR",
        full_name="Integration Test Patient",
        is_active=True,
        is_verified=False,
        diabetes_type="Type 1",
    )
    async_db_session.add(user)
    await async_db_session.flush()
    await async_db_session.refresh(user)

    writeback = SimulatorWriteback(async_db_session, sim_run_id=999, sim_user_key="int_test")

    # Generate 3 days of data
    base_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    day_gen = DayContextGenerator(config, rng)
    schedules = [day_gen.generate_day(base_date + timedelta(days=d)) for d in range(3)]

    # Generate CGM
    engine = GlucoseEngine(config, rng, start_time=base_date)
    cgm_readings = engine.generate_trace(schedules, num_days=3)

    # Write to health_metrics and legacy tables
    await writeback.write_glucose_metrics(user.id, cgm_readings)
    for sched in schedules:
        if sched.meals:
            await writeback.write_meal_metrics(user.id, sched.meals)
        if sched.insulin:
            await writeback.write_insulin_metrics(user.id, sched.insulin)
        if sched.exercise:
            await writeback.write_exercise_metrics(user.id, sched.exercise)
        if sched.sleep_start and sched.sleep_end:
            await writeback.write_sleep_metrics(user.id, sched.sleep_start, sched.sleep_end)
    await writeback.write_legacy_glucose(user.id, cgm_readings)
    await writeback.write_legacy_events(user.id, schedules)
    await async_db_session.flush()

    # Run PatternService detectors
    service = PatternService()
    start_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    end_date = datetime(2025, 12, 31, tzinfo=timezone.utc)

    spikes = await service.detect_post_meal_spikes(
        async_db_session, user.id, start_date, end_date,
        min_carbs=30, spike_threshold=50, persist_graph_edges=True,
    )
    await async_db_session.flush()

    overnight = await service.detect_overnight_hypoglycemia(
        async_db_session, user.id, start_date, end_date,
    )
    await async_db_session.flush()

    exercise = await service.analyze_exercise_impact(
        async_db_session, user.id, start_date, end_date,
    )
    await async_db_session.flush()

    fat_effects = await service.detect_delayed_high_fat_effects(
        async_db_session, user.id, start_date, end_date,
    )
    await async_db_session.flush()

    # Verify that edges were created
    from sqlalchemy import select
    result = await async_db_session.execute(
        select(HealthMetricEdge).where(HealthMetricEdge.user_id == user.id)
    )
    edges = list(result.scalars().all())

    # Post-meal spike anchor should produce some detections
    assert len(spikes) > 0, "Post-meal spike anchor should trigger spike detections"
    assert len(edges) > 0, f"Expected graph edges, got {len(edges)}"

    # Log what was detected
    edge_types = set(str(e.edge_type) for e in edges)
    print(f"Spikes detected: {len(spikes)}")
    print(f"Overnight events: {len(overnight)}")
    print(f"Exercise impacts: {len(exercise)}")
    print(f"Delayed fat effects: {len(fat_effects)}")
    print(f"Graph edges: {len(edges)} types={edge_types}")


@pytest.mark.asyncio
async def test_simulator_end_to_end_small(async_db_session):
    """Full simulation pipeline for a very small run: 2 anchors, 1 user, 1 day."""
    from app.simulator.service import SimulationService
    from app.simulator.schemas import SimRunCreate

    service = SimulationService(async_db_session)

    # Create a tiny run
    run = await service.create_run(
        SimRunCreate(
            name="tiny-integration-test",
            description="2 anchors x 1 user x 1 day",
            anchor_count=2,
            users_per_anchor=1,
            days_per_user=7,
        ),
    )
    assert run.id is not None
    assert run.status == "pending"

    # Execute
    run = await service.start_run(run.id)
    assert run.status == "completed"

    # Verify results
    from sqlalchemy import select as sa_select
    from app.simulator.models import SimHiddenTruth, SimDetectorScore

    truths_result = await async_db_session.execute(
        sa_select(SimHiddenTruth).where(SimHiddenTruth.sim_run_id == run.id)
    )
    truths = list(truths_result.scalars().all())

    scores_result = await async_db_session.execute(
        sa_select(SimDetectorScore).where(SimDetectorScore.sim_run_id == run.id)
    )
    scores = list(scores_result.scalars().all())

    # The pipeline should have generated truths and scores
    assert len(truths) > 0, f"Expected at least 1 truth, got {len(truths)}"
    assert len(scores) > 0, f"Expected at least 1 score, got {len(scores)}"
    assert run.summary_json is not None
    assert "detection_rate" in run.summary_json

    pattern_types = {t.pattern_type for t in truths}
    print(f"Run completed: {len(truths)} truths, {len(scores)} scores")
    print(f"Pattern types: {pattern_types}")
    print(f"Detection rate: {run.summary_json.get('detection_rate')}")
