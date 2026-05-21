#!/usr/bin/env python3
"""Test LibreLinkUp connection and fetch latest glucose data directly.

Usage:
  python scripts/test_librelinkup.py
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.librelinkup_service import (
    LibreLinkUpService,
    LibreLinkUpServiceError,
)


async def test_librelinkup_connection() -> None:
    """Test LibreLinkUp connection and display latest glucose reading."""
    
    # Read credentials from environment or docker-compose.prod.yml
    email = os.getenv("LIBRELINK_EMAIL", "tomm.batchelor@gmail.com")
    password = os.getenv("LIBRELINK_PASSWORD", "reJvy7-totzov-tabmes")
    region = os.getenv("LIBRELINK_REGION", "EU2")
    version = os.getenv("LIBRELINK_VERSION", "4.16.0")
    
    print(f"LibreLinkUp Connection Test")
    print(f"{'='*60}")
    print(f"   Email:  {email}")
    print(f"   Region: {region}")
    print(f"   API v:  {version}")
    print()
    
    service = LibreLinkUpService(
        email=email,
        password=password,
        region=region,
        version=version,
    )
    
    try:
        # Step 1 — Login
        print("1. Logging into LibreView...")
        ticket = await service.login()
        print(f"   ✅ Logged in! Token expires in {ticket.duration}s")
        print()
        
        # Step 2 — Get patient info
        print("2. Finding connected patient...")
        patient_id = await service.get_patient_id()
        print(f"   ✅ Found patient (ID: {patient_id})")
        print()
        
        # Step 3 — Latest reading
        print("3. Fetching latest glucose reading...")
        latest = await service.get_latest_glucose()
        if latest:
            ts = latest.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            print(f"   ✅ Value:     {latest.value_mg_dl} mg/dL")
            print(f"   ✅ Trend:     {service._trend_arrow_to_description(latest.trend_arrow)}")
            print(f"   ✅ Time:      {ts}")
        else:
            print("   ⚠️  No recent readings found")
        print()
        
        # Step 4 — 24h data stats
        print("4. Fetching recent readings...")
        readings = await service.get_glucose_readings(max_count=500)
        print(f"   ✅ Found {len(readings)} readings")
        
        if readings:
            values = [r.value_mg_dl for r in readings]
            time_range = readings[-1].timestamp, readings[0].timestamp
            
            print(f"\n   📊 24h Stats:")
            print(f"      Range:    {time_range[0].strftime('%H:%M')} — {time_range[1].strftime('%H:%M UTC')}")
            print(f"      Min:      {min(values)} mg/dL")
            print(f"      Max:      {max(values)} mg/dL")
            print(f"      Avg:      {sum(values)//len(values)} mg/dL")
            print(f"      Readings: {len(values)} total")
            
            # Show last 5 readings
            print(f"\n   📋 Last 5 readings:")
            for r in readings[:5]:
                trend = service._trend_arrow_to_description(r.trend_arrow)
                print(f"      {r.timestamp.strftime('%H:%M')}  {r.value_mg_dl:3.0f} mg/dL  {trend}")
        
        print(f"\n{'='*60}")
        print("✅ LibreLinkUp connection working!")
        print(f"   Your Libre data is being fetched directly from LibreView")
        print(f"{'='*60}")
        
    except LibreLinkUpServiceError as e:
        print(f"\n❌ LibreLinkUp error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_librelinkup_connection())