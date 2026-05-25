"""Production-ready T1D Companion service.

Architecture:
  Single consolidated LLM call (1 request, not 5)
  Deterministic nutrition from Postgres OpenFoodFacts
  Pure-math forecast engine (<1ms)
  Safety filter post-processor
  Redis/LRU cache for nutrition lookups
  FastAPI with async DB pool and structured logging

Usage:
  from app.t1d_companion.production.service import CompanionService
  service = CompanionService()
  result = await service.process(scenario="6 chicken wings", user_id="user_123")
"""