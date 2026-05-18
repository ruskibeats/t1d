# Todo #27: Fix error handling in API endpoints (P2)

Status: pending
Tags: #p2 #backend #bug
Branch: main

Wrap all `datetime.fromisoformat()` calls in try/except with proper 400 responses. Replace bare `except Exception` with specific exception types. Remove `str(e)` from error details returned to clients. Covers glucose_ext.py, environment.py, exercise.py, fasting.py, measurements.py, users.py, garmin.py, auth.py, patterns.py, insights.py.
