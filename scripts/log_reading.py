#!/usr/bin/env python3
"""Quick manual finger prick logger — log a reading from the terminal.

Usage:
    python scripts/log_reading.py 5.8 mmol/L          # UK units
    python scripts/log_reading.py 126 mg/dL           # US units
"""

import asyncio
import os
import sys

# Load .env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pathlib import Path
_env = Path(".env")
if _env.exists():
    for line in _env.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

from datetime import datetime, timezone


async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/log_reading.py <value> <unit>")
        print("  UK:  python scripts/log_reading.py 5.8 mmol/L")
        print("  US:  python scripts/log_reading.py 126 mg/dL")
        sys.exit(1)

    value = float(sys.argv[1])
    unit = sys.argv[2]

    from app.core.database import db_manager, get_settings
    from app.db.models import GlucoseReading, User
    from sqlalchemy import select

    settings = get_settings()
    db_manager.init_db(settings.database_url)

    async with db_manager.get_session() as session:
        # Get first user (or you'd use auth in production)
        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("❌ No users found. Create a user first.")
            sys.exit(1)

        # Convert to mg/dL for storage
        mgdl = value
        if unit.lower() in ("mmol/l", "mmol"):
            mgdl = round(value * 18.0182, 1)

        reading = GlucoseReading(
            user_id=user.id,
            glucose_value=mgdl,
            glucose_units="mg/dL",
            timestamp=datetime.now(timezone.utc).replace(tzinfo=None),
            reading_type="fingerstick",
            source="manual",
        )
        session.add(reading)
        await session.commit()

        from app.services.glucose_converter import format_glucose
        display = format_glucose(mgdl, unit if unit.lower() == "mg/dl" else "mmol/L")
        print(f"✅ Logged: {display} (finger prick)")
        print(f"   User: {user.email}")
        print(f"   Time: {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC")


asyncio.run(main())