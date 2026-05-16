"""Metrics domain package — unified health metric store.

All time-series health data (glucose, insulin, food, exercise, sleep,
measurements, vitals, lifestyle) flows through the health_metrics table.
Domain-specific tables exist only for complex multi-row structures
(exercise sets, sleep stages, meal ingredients).
"""