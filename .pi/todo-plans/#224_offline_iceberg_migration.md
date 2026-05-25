---
id: 224
title: Migrate Open Food Facts to Iceberg with validation pipeline
priority: high
status: pending
branch: feature/iceberg-migration
assignee: agent
tags: [data, backend, iceberg]
created: 2026-05-23
---

# Task: Migrate Open Food Facts to Iceberg with validation pipeline

## Context
- PostgreSQL OFF data cleaned (2.2M valid records)
- Iceberg catalog running at 192.168.0.248:8182
- Need streaming ingestion with validation

## Acceptance Criteria
- [ ] Stream OFF JSONL to Iceberg table
- [ ] Validate carbs range (0-300g) during ingestion
- [ ] Parse serving_size to standard units
- [ ] Add GI/GL columns (placeholder/enrichment step)
- [ ] Document Spark/Polars query patterns

## Technical Notes
- Use pyiceberg or Spark for ingestion
- Validate per-record, not batch
- Store as Parquet in Iceberg format
