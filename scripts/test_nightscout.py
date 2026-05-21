#!/usr/bin/env python3
"""Test Nightscout connection and fetch latest glucose data.

This script verifies that Nightscout integration is working correctly
for Libre CGM data.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.services.nightscout_service import NightscoutService, NightscoutServiceError


async def test_nightscout_connection() -> None:
    """Test Nightscout connection and display latest glucose reading."""
    settings = get_settings()
    
    # Check for Nightscout config
    ns_url = settings.nightscout_url
    ns_token = settings.nightscout_api_token
    
    if not ns_url:
        print("❌ NIGHTSCOUT_URL not configured in .env")
        print("   Add: NIGHTSCOUT_URL=https://your-nightscout-url.herokuapp.com")
        sys.exit(1)
    
    print(f"Testing Nightscout connection: {ns_url}")
    print(f"API Token: {'configured' if ns_token else 'not set (public NS?)'}")
    print()
    
    # Create service
    service = NightscoutService(
        base_url=ns_url,
        api_token=ns_token,
    )
    
    try:
        # Test connection
        print("1. Testing connection...")
        connected = await service._test_connection()
        if connected:
            print("   ✓ Connection successful")
        else:
            print("   ✗ Connection failed")
            sys.exit(1)
        
        # Get latest reading
        print("\n2. Fetching latest glucose reading...")
        latest = await service.get_latest_glucose()
        if latest:
            ts = datetime.fromtimestamp(latest.date / 1000, tz=timezone.utc)
            print(f"   ✓ Value: {latest.sgv} mg/dL")
            print(f"   ✓ Direction: {latest.direction or 'unknown'}")
            print(f"   ✓ Timestamp: {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("   ⚠ No recent readings found (last hour)")
        
        # Get 24h data
        print("\n3. Counting readings in last 24h...")
        from datetime import timedelta
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        
        readings = await service.get_glucose_readings(start, end, max_count=1000)
        print(f"   ✓ Found {len(readings)} readings in last 24 hours")
        
        if len(readings) > 0:
            print("\n✅ Nightscout integration working correctly!")
            print(f"   Your Libre data is accessible via {ns_url}")
        else:
            print("\n⚠ Connected but no recent data found")
            print("   Possible issues:")
            print("   - Nightscout not receiving data from Libre")
            print("   - Time zone mismatch")
            print("   - API token permissions")
        
    except NightscoutServiceError as e:
        print(f"\n❌ Nightscout error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify NIGHTSCOUT_URL is correct (no trailing slash)")
        print("2. Check API token if required")
        print("3. Ensure Nightscout is accessible from this machine")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(test_nightscout_connection())