# Clanker Ops #181: E6-F1 Add safety validator blocking dosing advice in forecast outputs

Status: pending
Tags: #meal-forecast #safety #validator #health-ai #e6

## Intended Outcome
Enforce a hard safety boundary so forecast responses cannot include insulin dose suggestions, correction advice, or wording that crosses from educational insight into medical dosing guidance.

## Scope
- Output validator
- Forbidden phrase/field detection
- Narrative sanitization or rejection

## Implementation Steps
1. Define banned output classes: insulin units recommended, correction factor advice, specific bolus timing advice, dose equivalence calculations
2. Add structured-field validator to block prohibited fields
3. Add narrative text scanner for unsafe phrases/patterns
4. Add remediation behavior: strip, rewrite, or fail closed
5. Add audit event when safety intervention occurs
6. Add regression tests using examples similar to the prototype's unsafe intermediate wording

## Acceptance Criteria
- Unsafe forecast outputs are blocked or rewritten
- Tests fail if dose-like language reappears
- Safety events are logged

## Dependencies
#180 - meal forecast engine must exist

## Done When
- Dosing advice cannot leak through forecast output paths.