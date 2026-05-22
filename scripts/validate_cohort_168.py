"""#168: Run 5-patient 7-day simulator cohort validation.

Executes a small simulator cohort, waits for completion, and reports
edge-creation and truth-detection evidence.
"""

import asyncio
import sys
import os

# Ensure app is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import db_manager, init_db
from app.simulator.service import SimulationService
from app.simulator.schemas import SimRunCreate


async def run_cohort():
    settings = get_settings()
    print(f"Database: {settings.database_url}")
    print()

    # Init DB
    await init_db()

    async with db_manager.get_session() as db:
        service = SimulationService(db)

        # 1. Check if there's already evidence in the system
        print("=" * 60)
        print("BEFORE: Checking pre-existing edges and truths...")
        print("=" * 60)

        try:
            result = await db.execute(text("SELECT COUNT(*) FROM health_metric_edges"))
            edge_count = result.scalar() or 0
            print(f"  health_metric_edges: {edge_count}")
        except Exception as e:
            print(f"  health_metric_edges: table not available ({e})")

        try:
            result = await db.execute(text("SELECT COUNT(*) FROM sim_hidden_truths"))
            truth_count = result.scalar() or 0
            print(f"  sim_hidden_truths: {truth_count}")
        except Exception as e:
            print(f"  sim_hidden_truths: table not available ({e})")

        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM sim_detector_scores")
            )
            score_count = result.scalar() or 0
            print(f"  sim_detector_scores: {score_count}")
        except Exception as e:
            print(f"  sim_detector_scores: table not available ({e})")

        print()

        # 2. Create a small run: 1 anchor x 5 users x 7 days
        print("=" * 60)
        print("Creating 5-patient, 7-day sim run...")
        print("=" * 60)

        run_data = SimRunCreate(
            name=f"validation-cohort-5x7-{asyncio.get_event_loop().time():.0f}",
            description="Small validation cohort: 5 patients x 7 days",
            anchor_count=1,
            users_per_anchor=5,
            days_per_user=7,
        )
        run = await service.create_run(run_data)
        print(f"  Run ID: {run.id}")
        print(f"  Name:   {run.name}")
        print(f"  Config: {run.anchor_count} anchor(s) × {run.users_per_anchor} users × {run.days_per_user} days")
        print()

        # 3. Start the run
        print("=" * 60)
        print("Starting simulation run... (this may take a minute)")
        print("=" * 60)

        started = await service.start_run(run.id)
        print(f"  Status: {started.status}")
        print()

        # 4. Report results
        print("=" * 60)
        print("AFTER: Results")
        print("=" * 60)

        # Refresh the run for summary
        await db.refresh(started)

        print(f"  Run status:       {started.status}")
        print(f"  Completed at:     {started.completed_at}")
        print(f"  Summary:          {started.summary_json}")

        # Edge count
        if started.summary_json:
            s = started.summary_json
            print(f"  Total users:      {s.get('total_users', '?')}")
            print(f"  Total truths:     {s.get('total_truths', '?')}")
            print(f"  Detections:       {s.get('total_detected', '?')}")
            print(f"  Detection rate:   {s.get('detection_rate', '?')}")
            print(f"  Avg recall:       {s.get('avg_recall', '?')}")
            print(f"  Avg precision:    {s.get('avg_precision', '?')}")
            print(f"  Avg f1:           {s.get('avg_f1', '?')}")

        print()

        # 5. Raw SQL evidence
        print("=" * 60)
        print("SQL EVIDENCE")
        print("=" * 60)

        try:
            result = await db.execute(text("SELECT COUNT(*) FROM health_metric_edges"))
            edge_count_after = result.scalar() or 0
            new_edges = edge_count_after - edge_count
            print(f"  health_metric_edges: {edge_count_after} ({new_edges:+d} new)")
        except Exception as e:
            print(f"  health_metric_edges: {e}")

        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM sim_hidden_truths WHERE sim_run_id = :rid"),
                {"rid": run.id},
            )
            truths = result.scalar() or 0
            print(f"  sim_hidden_truths (this run): {truths}")
        except Exception as e:
            print(f"  sim_hidden_truths: {e}")

        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM sim_detector_scores WHERE sim_run_id = :rid"),
                {"rid": run.id},
            )
            scores = result.scalar() or 0
            print(f"  sim_detector_scores (this run): {scores}")
        except Exception as e:
            print(f"  sim_detector_scores: {e}")

        try:
            result = await db.execute(
                text("SELECT COUNT(*) FROM sim_hidden_truths WHERE is_detected = true AND sim_run_id = :rid"),
                {"rid": run.id},
            )
            detected = result.scalar() or 0
            print(f"  Detected truths: {detected}")
        except Exception as e:
            print(f"  Detected truths: {e}")

        print()

        # 6. Verdict
        print("=" * 60)
        print("VERDICT")
        print("=" * 60)

        if started.status == "completed":
            detection_rate = (
                (started.summary_json.get("detection_rate", 0) if started.summary_json else 0)
                or 0
            )
            print(f"  ✅ Run completed successfully")
            print(f"  ✅ Detection rate: {detection_rate}")
            if detection_rate and detection_rate > 0:
                print(f"  ✅ FIX VERIFIED: Truth detection rate is non-zero (was 0% before fix)")
            else:
                print(f"  ⚠️  Detection rate is zero — fix may not be working")
        else:
            print(f"  ❌ Run status: {started.status}")

        return started


def main():
    result = asyncio.run(run_cohort())
    print()
    print("Done.")


if __name__ == "__main__":
    main()