"""Debug: Check latest sim run data."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.core.database import db_manager, init_db


async def check():
    await init_db()
    async with db_manager.get_session() as db:
        # Get the latest sim run
        result = await db.execute(
            text("SELECT id, name, status, summary_json FROM sim_runs ORDER BY id DESC LIMIT 1")
        )
        run = result.fetchone()
        print(f"Latest run: id={run.id}, name={run.name}, status={run.status}")
        print(f"  summary: {run.summary_json}")
        print()

        # Check sim users for latest run
        result = await db.execute(
            text("SELECT id, real_user_id, anchor_type FROM sim_users WHERE sim_run_id = :rid LIMIT 5"),
            {"rid": run.id},
        )
        users = result.fetchall()
        print(f"Sim users (run {run.id}): {len(users)}")
        for u in users:
            real_id = u.real_user_id
            # Check glucose data count
            hm = await db.execute(
                text("SELECT COUNT(*) FROM health_metrics WHERE user_id = :uid"),
                {"uid": real_id},
            )
            hm_count = hm.scalar()

            # Check date range
            dr = await db.execute(
                text("SELECT MIN(recorded_at), MAX(recorded_at) FROM health_metrics WHERE user_id = :uid"),
                {"uid": real_id},
            )
            dr_d = dr.fetchone()
            print(f"  sim_user={u.id}, real_user={real_id}, anchor={u.anchor_type}, "
                  f"metrics={hm_count}, dates={dr_d[0]} to {dr_d[1]}")

            # Check edges for this user
            edges = await db.execute(
                text("SELECT COUNT(*) FROM health_metric_edges WHERE user_id = :uid"),
                {"uid": real_id},
            )
            edge_count = edges.scalar()
            print(f"    edges={edge_count}")

            # Check hidden truths
            truths = await db.execute(
                text("SELECT COUNT(*) FROM sim_hidden_truths WHERE sim_user_id = :sid AND sim_run_id = :rid"),
                {"sid": u.id, "rid": run.id},
            )
            truth_count = truths.scalar()
            print(f"    hidden_truths={truth_count}")


asyncio.run(check())