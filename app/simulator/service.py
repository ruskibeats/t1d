"""Orchestrator service for the full simulation pipeline.

Coordinates:
1. Create simulation run + sim user records
2. Generate patient configs from anchors
3. Generate daily context schedules
4. Run glucose engine per patient
5. Write data into production tables (health_metrics + legacy)
6. Plant hidden truth labels
7. Run existing PatternService over synthetic data
8. Evaluate detector output against truths
"""

import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.pattern_service import PatternService
from app.simulator.anchors import list_anchor_profiles
from app.simulator.day_context import DayContextGenerator
from app.simulator.evaluator import SimulatorEvaluator
from app.simulator.glucose_engine import GlucoseEngine
from app.simulator.models import SimDetectorScore, SimRun, SimUser
from app.simulator.patient_factory import (
    generate_patient_config,
    generate_patient_batch,
    generate_profile_json,
)
from app.simulator.schemas import AnchorType, RunStatus, SimRunCreate
from app.simulator.truth_labels import TruthLabelPlacer
from app.simulator.writeback import SimulatorWriteback

logger = logging.getLogger(__name__)


class SimulationService:
    """Orchestrates end-to-end simulation runs."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.pattern_service = PatternService()

    # ── Run Management ──

    async def create_run(self, data: SimRunCreate, created_by: Optional[int] = None) -> SimRun:
        """Create a new simulation run record.

        Args:
            data: Run creation parameters.
            created_by: Optional user ID who initiated the run.

        Returns:
            Created SimRun instance.
        """
        run = SimRun(
            name=data.name,
            description=data.description,
            status=RunStatus.PENDING.value,
            anchor_count=data.anchor_count,
            users_per_anchor=data.users_per_anchor,
            days_per_user=data.days_per_user,
            config_json=data.config_json,
            created_by=created_by,
        )
        self.db.add(run)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(run)
        logger.info(f"Created sim run: {run.id} '{run.name}'")
        return run

    async def start_run(self, run_id: int) -> SimRun:
        """Execute a full simulation run from generation through evaluation.

        Args:
            run_id: SimRun.id to execute.

        Returns:
            SimRun with updated status and summary.
        """
        result = await self.db.execute(select(SimRun).where(SimRun.id == run_id))
        run = result.scalar_one_or_none()
        if not run:
            raise ValueError(f"SimRun {run_id} not found")

        # Clear any stale transaction from a previous failed query
        await self.db.rollback()

        run.status = RunStatus.GENERATING.value
        run.started_at = datetime.now(timezone.utc)
        await self.db.flush()

        try:
            # Determine which anchor profiles to use
            anchors = list_anchor_profiles()
            anchor_types = [a.anchor_type for a in anchors[:run.anchor_count]]

            total_users = len(anchor_types) * run.users_per_anchor
            logger.info(
                f"Starting sim run {run_id}: {len(anchor_types)} anchors x "
                f"{run.users_per_anchor} users x {run.days_per_user} days = "
                f"{total_users} patients, {total_users * run.days_per_user} total days"
            )

            # Process each anchor group
            all_user_records: list[dict] = []
            total_truths = 0
            user_index = 0

            for anchor_type in anchor_types:
                configs = generate_patient_batch(
                    anchor_type, run.users_per_anchor, start_seed=run.id * 10000 + user_index * 100
                )

                for i, config in enumerate(configs):
                    sim_user_key = f"sim_{run.id}_{anchor_type.value}_{i + 1:03d}"
                    profile_json = generate_profile_json(config)
                    rng = random.Random(config.seed)

                    logger.info(
                        f"Generating patient {sim_user_key} "
                        f"(anchor={anchor_type.value}, day_count={run.days_per_user})"
                    )

                    # Generate daily schedules
                    day_gen = DayContextGenerator(config, rng)
                    base_date = datetime.now(timezone.utc).replace(
                        year=2025, month=1, day=1,
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    schedules = [
                        day_gen.generate_day(base_date + timedelta(days=d))
                        for d in range(run.days_per_user)
                    ]

                    # Run glucose engine
                    engine = GlucoseEngine(config, rng, start_time=base_date)
                    cgm_readings = engine.generate_trace(schedules, run.days_per_user)

                    # Write data
                    writeback = SimulatorWriteback(self.db, run.id, sim_user_key)
                    real_user = await writeback.register_sim_user(config, profile_json)

                    await writeback.write_legacy_glucose(real_user.id, cgm_readings)
                    await writeback.write_legacy_events(real_user.id, schedules)

                    # Write to health_metrics
                    await writeback.write_glucose_metrics(real_user.id, cgm_readings)

                    # Write events as metrics
                    for sched in schedules:
                        if sched.meals:
                            await writeback.write_meal_metrics(real_user.id, sched.meals)
                        if sched.insulin:
                            await writeback.write_insulin_metrics(real_user.id, sched.insulin)
                        if sched.exercise:
                            await writeback.write_exercise_metrics(real_user.id, sched.exercise)
                        if sched.sleep_start and sched.sleep_end:
                            await writeback.write_sleep_metrics(
                                real_user.id, sched.sleep_start, sched.sleep_end
                            )

                    await self.db.flush()

                    # Create SimUser record
                    sim_user = SimUser(
                        sim_run_id=run.id,
                        sim_user_key=sim_user_key,
                        anchor_type=anchor_type.value,
                        real_user_id=real_user.id,
                        parameter_json=config.model_dump(),
                        profile_json=profile_json,
                        seed=config.seed,
                    )
                    self.db.add(sim_user)
                    await self.db.flush()
                    await self.db.refresh(sim_user)

                    # Plant truth labels
                    placer = TruthLabelPlacer(self.db, run.id)
                    truths = await placer.plant_all_truths(
                        sim_user_id=sim_user.id,
                        user_id=real_user.id,
                        config=config,
                        daily_schedules=schedules,
                        cgm_readings=cgm_readings,
                        sim_user_key=sim_user_key,
                    )
                    total_truths += len(truths)

                    all_user_records.append({
                        "sim_user_key": sim_user_key,
                        "anchor_type": anchor_type.value,
                        "user_id": real_user.id,
                        "sim_user_id": sim_user.id,
                        "cgm_readings": len(cgm_readings),
                        "truths_planted": len(truths),
                    })

                    user_index += 1

                    # Log progress periodically
                    if user_index % 10 == 0:
                        logger.info(
                            f"Progress: {user_index}/{total_users} patients generated "
                            f"({user_index/total_users*100:.0f}%)"
                        )

            # Run existing PatternService detectors on all sim users
            run.status = RunStatus.EVALUATING.value
            await self.db.flush()

            logger.info(f"Running PatternService detectors for {len(all_user_records)} users...")
            for record in all_user_records:
                await self._run_detectors(record["user_id"])
            logger.info("Detector run complete")

            # Run evaluation
            evaluator = SimulatorEvaluator(self.db, run.id)
            summary = await evaluator.run_evaluation(run)

            logger.info(
                f"Sim run {run_id} complete. "
                f"Detection rate: {summary.get('detection_rate', 'N/A')}"
            )

            # Commit the completed state
            await self.db.commit()
            await self.db.refresh(run)
            logger.info(f"Commit succeeded for run {run_id}")
            return run

        except Exception as e:
            run.status = RunStatus.FAILED.value
            run.notes = f"Failed at {datetime.now(timezone.utc).isoformat()}: {str(e)}"
            try:
                await self.db.flush()
                await self.db.commit()
            except Exception:
                pass  # Already in error state
            logger.error(f"Sim run {run_id} failed: {e}", exc_info=True)
            raise

    async def _run_detectors(self, user_id: int) -> None:
        """Run PatternService detectors over a user's synthetic data.

        This exercises the exact same detection paths used for real users.

        Args:
            user_id: The real_user_id (from tbl_users).
        """
        try:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=365)  # Wide enough to cover all sim data

            # Run all detectors — these create edges in health_metric_edges
            await self.pattern_service.detect_post_meal_spikes(
                self.db, user_id, start_date, end_date,
                min_carbs=30, spike_threshold=50, persist_graph_edges=True,
            )
            await self.pattern_service.detect_overnight_hypoglycemia(
                self.db, user_id, start_date, end_date,
            )
            await self.pattern_service.analyze_exercise_impact(
                self.db, user_id, start_date, end_date,
            )
            await self.pattern_service.detect_delayed_high_fat_effects(
                self.db, user_id, start_date, end_date,
            )
            await self.db.flush()
        except Exception as e:
            logger.warning(f"Detector run failed for user {user_id}: {e}")

    # ── Query Methods ──

    async def get_run(self, run_id: int) -> Optional[SimRun]:
        """Get a simulation run by ID.

        Args:
            run_id: SimRun.id.

        Returns:
            SimRun or None.
        """
        result = await self.db.execute(select(SimRun).where(SimRun.id == run_id))
        return result.scalar_one_or_none()

    async def list_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
    ) -> tuple[list[SimRun], int]:
        """List simulation runs with optional status filter.

        Args:
            limit: Max results.
            offset: Pagination offset.
            status: Optional status filter.

        Returns:
            (runs, total_count) tuple.
        """
        query = select(SimRun)
        count_query = select(func.count(SimRun.id))

        if status:
            query = query.where(SimRun.status == status)
            count_query = count_query.where(SimRun.status == status)

        query = query.order_by(SimRun.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        runs = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return runs, total

    async def get_run_users(
        self,
        run_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[SimUser], int]:
        """Get sim users for a run.

        Args:
            run_id: SimRun.id.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            (users, total_count) tuple.
        """
        query = (
            select(SimUser)
            .where(SimUser.sim_run_id == run_id)
            .order_by(SimUser.anchor_type, SimUser.sim_user_key)
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count(SimUser.id)).where(SimUser.sim_run_id == run_id)

        result = await self.db.execute(query)
        users = list(result.scalars().all())

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        return users, total

    async def get_truths(
        self,
        run_id: int,
        sim_user_id: Optional[int] = None,
        pattern_type: Optional[str] = None,
    ) -> list[dict]:
        """Get hidden truths for a run, optionally filtered.

        Args:
            run_id: SimRun.id.
            sim_user_id: Optional SimUser.id filter.
            pattern_type: Optional pattern type filter.

        Returns:
            List of truth dicts.
        """
        from app.simulator.models import SimHiddenTruth

        query = select(SimHiddenTruth).where(SimHiddenTruth.sim_run_id == run_id)
        if sim_user_id:
            query = query.where(SimHiddenTruth.sim_user_id == sim_user_id)
        if pattern_type:
            query = query.where(SimHiddenTruth.pattern_type == pattern_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_scores(
        self,
        run_id: int,
        anchor_type: Optional[str] = None,
        pattern_type: Optional[str] = None,
    ) -> list[SimDetectorScore]:
        """Get detector scores for a run.

        Args:
            run_id: SimRun.id.
            anchor_type: Optional anchor type filter.
            pattern_type: Optional pattern type filter.

        Returns:
            List of SimDetectorScore.
        """
        from app.simulator.models import SimDetectorScore

        query = select(SimDetectorScore).where(SimDetectorScore.sim_run_id == run_id)
        if anchor_type:
            query = query.where(SimDetectorScore.anchor_type == anchor_type)
        if pattern_type:
            query = query.where(SimDetectorScore.pattern_type == pattern_type)

        query = query.order_by(SimDetectorScore.metric_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())
