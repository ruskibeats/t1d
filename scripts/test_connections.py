#!/usr/bin/env python3
"""
Test both CGM data connections: Libre (via Nightscout), LibreLinkUp (direct), and Dexcom.

Usage:
  python scripts/test_connections.py                    # Test all
  python scripts/test_connections.py --libre             # Test Libre via Nightscout only
  python scripts/test_connections.py --librelinkup       # Test LibreLinkUp direct only
  python scripts/test_connections.py --dexcom            # Test Dexcom only
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings


# ──────────────────────────────────────────────
# Section 1: Libre CGM (via Nightscout)
# ──────────────────────────────────────────────

async def test_libre_connection() -> int:
    """Test Nightscout connection for Libre data. Returns 0 on success."""
    from app.services.nightscout_service import NightscoutService, NightscoutServiceError

    settings = get_settings()
    ns_url = settings.nightscout_url
    ns_token = settings.nightscout_api_token

    if not ns_url or "your-nightscout" in (ns_url or ""):
        print("  ⏭  Skipped — NIGHTSCOUT_URL not configured (placeholder value)")
        print("     Set it in .env and re-run")
        return 0  # skipped, not a failure

    print(f"\n{'='*60}")
    print("📡  TEST 1: Libre CGM (via Nightscout)")
    print(f"{'='*60}")
    print(f"   URL:  {ns_url}")
    print(f"   Auth: {'API token set' if ns_token else 'no token (public NS?)'}")
    print()

    service = NightscoutService(base_url=ns_url, api_token=ns_token)

    try:
        # Step 1 — Connection
        print("  1. Testing Nightscout connection...")
        await service._test_connection()
        print("     ✅ Connection successful")

        # Step 2 — Latest reading
        print("\n  2. Fetching latest glucose reading...")
        latest = await service.get_latest_glucose()
        if latest:
            ts = datetime.fromtimestamp(latest.date / 1000, tz=timezone.utc)
            print(f"     ✅ Value:     {latest.sgv} mg/dL")
            print(f"     ✅ Direction: {latest.direction or 'unknown'}")
            print(f"     ✅ Time:      {ts.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("     ⚠️  No readings found in the last hour")

        # Step 3 — 24h data count
        print("\n  3. Counting readings in last 24h...")
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=24)
        readings = await service.get_glucose_readings(start, end, max_count=1000)
        print(f"     {'✅' if readings else '⚠️'}  Found {len(readings)} readings in last 24 hours")

        if readings:
            values = [r.sgv for r in readings]
            print(f"\n     📊 Stats:")
            print(f"        Min:    {min(values)} mg/dL")
            print(f"        Max:    {max(values)} mg/dL")
            print(f"        Avg:    {sum(values)//len(values)} mg/dL")
            print(f"        Range:  {len(readings)} readings over 24h")
            print(f"        Freq:   ~{24*60 // len(readings) if readings else 0} min between readings")

        print(f"\n  ✅ Libre (Nightscout) integration working!")
        return 0

    except NightscoutServiceError as e:
        print(f"\n  ❌ Nightscout error: {e}")
        print("\n  Troubleshooting:")
        print("     1. Verify NIGHTSCOUT_URL is correct")
        print("     2. Check API token permissions")
        print("     3. Ensure Libre uploader is sending data")
        print("     4. Check network/firewall access")
        return 1
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {e}")
        return 1


# ──────────────────────────────────────────────
# Section 2: Dexcom CGM
# ──────────────────────────────────────────────

async def test_dexcom_connection() -> int:
    """Test Dexcom API connection. Returns 0 on success."""
    from app.services.dexcom_service import DexcomService, DexcomServiceError

    settings = get_settings()
    client_id = settings.dexcom_client_id
    client_secret = settings.dexcom_client_secret

    if not client_id or "your-dexcom" in (client_id or ""):
        print(f"\n{'='*60}")
        print("📡  TEST 2: Dexcom CGM")
        print(f"{'='*60}")
        print("  ⏭  Skipped — DEXCOM_CLIENT_ID not configured (placeholder value)")
        print("     Register at https://developer.dexcom.com/")
        print("     Then set DEXCOM_CLIENT_ID and DEXCOM_CLIENT_SECRET in .env")
        return 0  # skipped

    print(f"\n{'='*60}")
    print("📡  TEST 2: Dexcom CGM")
    print(f"{'='*60}")
    print(f"   Environment: {'SANDBOX' if settings.dexcom_use_sandbox else 'PRODUCTION'}")
    print()

    # Use sandbox for testing unless explicitly set to production
    service = DexcomService(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=settings.dexcom_redirect_uri or "http://localhost:8000/auth/dexcom/callback",
        use_sandbox=settings.dexcom_use_sandbox,
    )

    try:
        # Step 1 — Verify OAuth URL generation works
        print("  1. Generating OAuth authorization URL...")
        auth_url = service.get_authorization_url(state="test-connection")
        print(f"     ✅ Authorization URL:")
        print(f"        {auth_url}")

        # Step 2 — This is where Dexcom differs from Nightscout
        # Dexcom uses OAuth2 — you need to visit the URL, authorize, and get a code.
        # We can't fully test data retrieval without going through the OAuth flow.
        print(f"\n  2. ⚠️  Full data test requires OAuth2 flow:")
        print(f"     i)   Visit the authorization URL above in a browser")
        print(f"     ii)  Authorize the app")
        print(f"     iii) Copy the authorization code from the callback URL")
        print(f"     iv)  Run a token exchange")

        print(f"\n  ⚠️  Dexcom uses OAuth2 — can't test fully via CLI alone.")
        print(f"     To complete setup, start the API server and visit:")
        print(f"\n     {settings.dexcom_base_url or 'https://sandbox-api.dexcom.com/v2'}/oauth2/auth?")
        print(f"         client_id={client_id}&")
        print(f"         redirect_uri=http://localhost:8000/auth/dexcom/callback&")
        print(f"         response_type=code&")
        print(f"         scope=offline_access")
        print()
        return 0

    except DexcomServiceError as e:
        print(f"\n  ❌ Dexcom error: {e}")
        return 1
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {e}")
        return 1


# ──────────────────────────────────────────────
# Section 3: LibreLinkUp (Direct)
# ──────────────────────────────────────────────

async def test_librelinkup_connection() -> int:
    """Test LibreLinkUp direct connection. Returns 0 on success."""
    from app.services.librelinkup_service import LibreLinkUpService, LibreLinkUpServiceError

    email = os.getenv("LIBRELINK_EMAIL", "tomm.batchelor@gmail.com")
    password = os.getenv("LIBRELINK_PASSWORD", "reJvy7-totzov-tabmes")
    region = os.getenv("LIBRELINK_REGION", "EU2")

    print(f"\n{'='*60}")
    print("📡  TEST 3: LibreLinkUp (Direct)")
    print(f"{'='*60}")
    print(f"   Email:  {email}")
    print(f"   Region: {region}")
    print()

    service = LibreLinkUpService(email=email, password=password, region=region)

    try:
        print("  1. Logging into LibreView...")
        await service.login()
        print("     ✅ Logged in!")

        print("\n  2. Finding connected patient...")
        await service.get_patient_id()
        print("     ✅ Patient found")

        print("\n  3. Fetching latest glucose reading...")
        latest = await service.get_latest_glucose()
        if latest:
            print(f"     ✅ Value: {latest.value_mg_dl} mg/dL")
            print(f"     ✅ Trend: {service._trend_arrow_to_description(latest.trend_arrow)}")
            print(f"     ✅ Time:  {latest.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        else:
            print("     ⚠️  No recent readings")

        print("\n  4. Counting readings...")
        readings = await service.get_glucose_readings(max_count=500)
        print(f"     ✅ Found {len(readings)} readings")

        if readings:
            values = [r.value_mg_dl for r in readings]
            print(f"     Min: {min(values)} mg/dL, Max: {max(values)} mg/dL, Avg: {sum(values)//len(values)} mg/dL")

        print(f"\n  ✅ LibreLinkUp direct connection working!")
        return 0

    except LibreLinkUpServiceError as e:
        print(f"\n  ❌ LibreLinkUp error: {e}")
        return 1
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {e}")
        return 1


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

async def main():
    args = set(sys.argv[1:])
    test_all = not args or "--all" in args
    test_libre = test_all or "--libre" in args
    test_librelinkup = test_all or "--librelinkup" in args
    test_dexcom = test_all or "--dexcom" in args

    print("=" * 60)
    print("🔬  T1D Companion — CGM Connection Tests")
    print("=" * 60)

    exit_code = 0

    if test_libre:
        ec = await test_libre_connection()
        exit_code = exit_code or ec

    if test_librelinkup:
        ec = await test_librelinkup_connection()
        exit_code = exit_code or ec

    if test_dexcom:
        ec = await test_dexcom_connection()
        exit_code = exit_code or ec

    print(f"\n{'='*60}")
    if exit_code == 0:
        print("✅  All tests completed")
    else:
        print("❌  Some tests failed — see above")
    print("=" * 60)

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())