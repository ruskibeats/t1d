# Todo #26: Add input validation to all API endpoints (P1)

Status: pending
Tags: #p1 #backend #security
Branch: main

Add `Query(ge=0, le=MAX)` constraints to all limit/offset/skip/window_minutes parameters. Add `max_length` to all string query parameters. Covers chat.py, glucose.py, events.py, users.py, food.py, environment.py, exercise.py, fasting.py, measurements.py, and all data domain files.
