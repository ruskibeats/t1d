"""Test meal impact query against a random sim user."""
import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import datetime, timezone
from sqlalchemy import text
from app.core.database import db_manager, init_db


async def test():
    await init_db()
    async with db_manager.get_session() as db:
        # Grab a random sim user
        result = await db.execute(text("""
            SELECT u.id, u.email FROM tbl_users u 
            JOIN sim_users su ON su.real_user_id = u.id 
            WHERE u.email LIKE 'sim_%'
            ORDER BY RANDOM() LIMIT 1
        """))
        user = result.fetchone()
        print(f"User: {user.email} (id={user.id})")

        from app.food.service import FoodService
        svc = FoodService(db)

        result = await svc.estimate_meal_impact(
            user_id=user.id,
            items=["fried eggs", "warburtons thick sliced toast", "butter"],
            eaten_at=datetime(2026, 5, 21, 19, 0, tzinfo=timezone.utc),
        )

        print(json.dumps(result, indent=2, default=str))


asyncio.run(test())