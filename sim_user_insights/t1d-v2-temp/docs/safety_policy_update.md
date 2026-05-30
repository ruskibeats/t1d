# Safety Policy - Product Boundary Clarification

## Current Status
The companion explicitly does NOT prescribe insulin. All "estimates" are educational/simulation only.

## What Was Removed
- `bolus_estimate` field from LLM bundle (removed from stage_companion_advice)

## What Remains
The LLM bundle now contains:
- `carb_ratio` (profile parameter, for context only)
- `insulin_sensitivity` (profile parameter, for context only)  
- NO bolus/unit estimates of any kind

## Rationale
- Companion is observer/explainer, not controller
- Any unit estimate creates product intent ambiguity
- Safety rules now block all dosing references at the prompt level

## Enforcement
1. `t1d_llm_context.py` contains banned words list
2. `companion_system.txt` prompt reinforces "educational only"  
3. `safety_rules.txt` blocks dosing instructions
4. Golden tests verify no dosing language in output