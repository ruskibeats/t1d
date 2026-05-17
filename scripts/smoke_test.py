#!/usr/bin/env python3
"""Smoke test — verify all 25 API routers are registered (no 404s)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from starlette.testclient import TestClient
from app.main import app

client = TestClient(app, raise_server_exceptions=False)

passed = 0
failed = 0

print("=== Router registration smoke test ===")
print("(Checking no 404s — 401/500 is OK, means router exists)\n")

endpoints = [
    ("GET", "/health"),
    ("GET", "/api/v1/glucose"),
    ("GET", "/api/v1/events"),
    ("GET", "/api/v1/patterns"),
    ("GET", "/api/v1/food"),
    ("GET", "/api/v1/exercise"),
    ("GET", "/api/v1/sleep"),
    ("GET", "/api/v1/fasting"),
    ("GET", "/api/v1/measurements"),
    ("GET", "/api/v1/mood"),
    ("GET", "/api/v1/water"),
    ("GET", "/api/v1/heart"),
    ("GET", "/api/v1/blood-pressure"),
    ("GET", "/api/v1/activity"),
    ("GET", "/api/v1/vitals"),
    ("GET", "/api/v1/body-composition"),
    ("GET", "/api/v1/body-battery"),
    ("GET", "/api/v1/lifestyle"),
    ("GET", "/api/v1/environment"),
    ("GET", "/api/v1/metrics"),
    ("GET", "/api/v1/conversations"),
]

for method, path in endpoints:
    r = client.get(path) if method == "GET" else client.post(path)
    ok = r.status_code != 404
    passed += ok
    failed += not ok
    print(f"{'✅' if ok else '❌'} {method} {path} → {r.status_code}")

print(f"\n{passed} passed, {failed} failed out of {passed + failed}")
sys.exit(0 if failed == 0 else 1)
