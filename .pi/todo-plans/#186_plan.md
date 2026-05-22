# Clanker Ops #186: E11-F1 Add food-quality flags and duplicate detection rules

Status: pending
Tags: #meal-forecast #food-quality #duplicate-detection #data-quality #e11

## Intended Outcome
Improve food input trustworthiness by scoring rows for quality and detecting likely duplicates in branded/community-contributed food data.

## Scope
- Food quality flags
- Duplicate detection heuristics
- Source trust ranking
- Forecast confidence integration

## Implementation Steps
1. Define quality flags: missing carbs, missing serving grams, missing calories, barcode absent, conflicting duplicate barcode, implausible macro totals, community-only row, stale source row
2. Add duplicate detection rules: same barcode different nutrient values, near-identical name + brand + serving size, normalized name collisions
3. Add food source trust tier field if not present
4. Add duplicate candidate table or JSON field for review
5. Integrate food quality score into nutrient extraction output
6. Add confidence downgrade rules in forecast engine when low-quality foods present
7. Add tests with duplicate and incomplete food fixtures

## Acceptance Criteria
- Every resolved food row carries quality flags
- Duplicate detection identifies obvious branded duplicates
- Forecast confidence is lowered when meal quality is weak

## Dependencies
#185 - simulator scenario suite must exist

## Done When
- Food quality is visible and affects forecast confidence.