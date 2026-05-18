# Todo #25: Add auth guards to 13 unauthenticated endpoint files (P0)

Status: pending
Tags: #p0 #backend #security
Branch: main

Add `Depends(require_active_user)` to all unauthenticated endpoints in: fasting.py, measurements.py, mood.py, sleep.py, water.py, metrics.py, fitbit.py, garmin.py, polar.py, strava.py, withings.py. Replace `user_id: int = Query(...)` with `user.id` from the authenticated user object.
