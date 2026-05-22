# Clanker Ops #182: E7-F1 Add deterministic narrative template generator

Status: pending
Tags: #meal-forecast #narrative #templates #llm #e7

## Intended Outcome
Generate safe, consistent user-facing explanations from structured forecast evidence using deterministic templates first, with optional LLM rewrite only after safety validation.

## Scope
- Template-based narrative generation
- Optional post-template rewrite hook
- No reasoning delegated to LLM

## Implementation Steps
1. Define narrative input contract from forecast object
2. Create template sections: meal summary, likely timing, risk explanation, personal context note, confidence note, safety note
3. Build deterministic renderer
4. Add optional rewrite interface behind feature flag
5. Ensure safety validator runs after any rewrite
6. Add tests for wording under each risk/confidence combination

## Acceptance Criteria
- Narrative can be produced without LLM access
- Final text is grounded in evidence fields only
- No direct dosing advice appears

## Dependencies
#181 - safety validator must exist

## Done When
- Forecast explanation is stable, safe, and evidence-backed.