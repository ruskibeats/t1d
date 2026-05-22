"""Test: pick a random sim user, ask what happens if they drink 5% lager."""
import asyncio
import json
import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from app.core.database import db_manager
from app.config import get_settings


async def test():
    settings = get_settings()
    db_manager.init_db(settings.database_url)

    async with db_manager.get_session() as db:
        # 1. Pick a random sim user
        result = await db.execute(text("""
            SELECT u.id, u.email FROM tbl_users u
            JOIN sim_users su ON su.real_user_id = u.id
            WHERE u.email LIKE 'sim_%'
            ORDER BY RANDOM() LIMIT 1
        """))
        user = result.fetchone()
        print(f"User: {user.email} (id={user.id})")

        # 2. Check their recent glucose
        glu = await db.execute(text("""
            SELECT value, measured_at FROM health_metrics
            WHERE user_id = :uid AND type = 'blood_glucose'
            ORDER BY measured_at DESC LIMIT 5
        """), {"uid": user.id})
        recent_glucose = glu.fetchall()
        print(f"\nRecent glucose:")
        for g in recent_glucose:
            print(f"  {g.measured_at}: {g.value} mg/dL")

        # 3. Search for lager in OFF
        products = await db.execute(text("""
            SELECT code, product_name, brands, serving_size,
                   carbs_100g, proteins_100g, fat_100g, energy_kcal_100g
            FROM openfoodfacts_products
            WHERE product_name ILIKE '%lager%' AND product_name ILIKE '%beer%'
            LIMIT 5
        """))
        beers = products.fetchall()
        print(f"\nMatched beers:")
        for b in beers:
            kcal = b.energy_kcal_100g if b.energy_kcal_100g is not None else 0
            print(f"  {b.product_name} ({b.brands}): carbs={b.carbs_100g}g/100ml, kcal={kcal:.0f}/100ml")

        # 4. Use FoodService to get meal impact
        from app.food.service import FoodService
        svc = FoodService(db)

        result = await svc.estimate_meal_impact(
            user_id=user.id,
            items=["5% lager beer", "lager"],
            eaten_at=datetime.now(timezone.utc),
        )

        print(f"\n=== MEAL IMPACT FORECAST ===")
        print(f"Question: {result.get('question', '?')}")
        print(f"Eaten at: {result.get('eaten_at', '?')}")
        print(f"\nMatched items: {len(result.get('matched_items', []))}")
        for item in result.get('matched_items', []):
            print(f"  {item.get('name','?')}: {item.get('carbs_g','?')}g carbs, {item.get('calories','?')} kcal")
        print(f"Unmatched: {result.get('unmatched_items', [])}")

        print(f"\nMeal totals: {json.dumps(result.get('meal_totals', {}), indent=2)}")

        print(f"\nGlucose context:")
        ctx = result.get('glucose_context', {})
        print(f"  Current: {ctx.get('current_glucose', '?')} mg/dL")
        print(f"  Trend: {ctx.get('trend', '?')}")

        print(f"\nForecast:")
        fc = result.get('forecast', {})
        print(f"  Risk: {fc.get('risk_level', '?')}")
        print(f"  Peak rise: {fc.get('expected_peak_rise', '?')}")
        print(f"  Timing: {fc.get('timing', '?')}")
        print(f"  Confidence: {fc.get('confidence', '?')}")

        print(f"\nSafety note: {result.get('safety_note', '?')}")


asyncio.run(test())