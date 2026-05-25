---
id: 225
title: Update NLP scripts to use real OFF database data
priority: high
status: pending
branch: feature/nlp-off-integration
assignee: agent
tags: [nlp, food, backend]
created: 2026-05-23
---

# Task: Update NLP scripts to use real OFF database data

## Context
- NLP scripts currently use estimated values
- Need to query real OFF data for accurate carbs
- User: "2 donuts and coke" needs real nutrition lookup

## Acceptance Criteria
- [ ] Create /food/search endpoint using real OFF data
- [ ] Update natural_language_demo.py to use database
- [ ] Update cli_chat.py with real queries
- [ ] Match foods user has eaten previously first

## Technical Notes
- Query by product_name ILIKE '%donut%'
- Parse serving_size → grams for carb calculation
- Fallback to estimates if no match
