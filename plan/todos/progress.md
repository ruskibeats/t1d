# Progress

## Status
Active — Graph + Photo Ingest focus

## Active Sprint
Sprint 1 (Safety) ✅ complete
Sprint 2-5: Pending
Graph tasks: In progress (event grouping, migrations, service layer, edges, provenance, confidence, photo ingest)

## Files Changed (2026-05-18)
- plan/ folder structure created (specs/, todos/, decisions/, reports/)
- plan/todos/MASTER_TODO.md — consolidated from GRAPH_TODO.md + SPRINT_PLAN.md + phase plans
- plan/README.md — folder index
- DOCUMENTATION_INDEX.md — updated for new structure
- DATA_DESIGN_FLOW_PLAN.md — food resolution layer added
- GRAPH_TODO.md — food resolution + photo provenance tasks added
- FRONTEND_DESIGN.md — food resolution in meal review flow

## Key Decisions
- Vision model is a proposal step only; food resolution layer owns nutrition mapping
- Source trust hierarchy: user-confirmed → curated/Sparky → standardized DBs → open community → model fallback
- Canonical food model: food_source_records, canonical_foods, food_aliases, meal_item_candidates, meal_items
- Graph edges are observational evidence, not treatment advice
- todo tool tasks loaded into memory for session persistence via branch replay

## Next Up
1. Event grouping foundation (event_group_id on health_metrics)
2. Exercise graph edges + tests
3. Delayed high-fat graph edges + tests
4. Food resolution service implementation
5. Frontend screen consolidation (Sprint 2)
