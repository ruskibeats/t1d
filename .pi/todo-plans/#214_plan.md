# Clanker Ops #214: Calibrate post_meal_spike and brittle anchors

## Intended Outcome
post_meal_spike: baseline 90-160, one meal spikes to 200-240, 0% ceiling.
brittle: range 60-280 with irregular responses, <5% ceiling.

## Blocked By
This task is blocked by #213 (cumulative drift fix). Don't start until #213 is verified.

## Post_meal_spike Target Spec
- Daytime baseline: 90-160 (currently 130-190 — needs drift fix)
- One meal (lunch): 200-240 peak with 70-120 mg/dL rise (currently 335 — reduce meal_rise or under-bolus)
- Other meals: 140-175 (well-controlled)
- 0% at ceiling ✅ already acheived in current calibration
- TIR target: >60%

## Brittle Target Spec  
- Range: 60-280 (currently 106-415)
- Erratic meal responses with delayed recovery
- Occasional >300 excursions but <5% at ceiling
- TIR target: ~40-50%
- Should clearly look different from well_controlled on visual inspection

## Parameters to Tune
1. **post_meal_spike**: Increase under_bolus_factor for lunch from 0.75 to 0.80 (reduce spike height), keep other meals at 0.90 (well-bolused). Reduce lunch size if needed.
2. **brittle**: Reduce under-bolus variability from 0.65±0.10 to 0.70±0.12. Reduce dinner size. Increase noise_sd for more chaotic appearance without hitting ceiling.

## Verification
```bash
python -c "import random; from datetime import datetime, timezone, timedelta; from app.simulator.schemas import AnchorType; from app.simulator.patient_factory import generate_patient_config; from app.simulator.day_context import DayContextGenerator; from app.simulator.glucose_engine import GlucoseEngine; config=generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42); rng=random.Random(config.seed); ctx=DayContextGenerator(config, rng); schedules=[ctx.generate_day(datetime(2025,1,d+1,tzinfo=timezone.utc)) for d in range(3)]; engine=GlucoseEngine(config, rng); r=engine.generate_trace(schedules); v=[x['glucose_value'] for x in r]; print(f'range=[{min(v):.0f},{max(v):.0f}] avg={sum(v)/len(v):.0f} ceil={100*sum(1 for x in v if x>=395)/len(v):.0f}%')"
```

## Files to modify
- `app/simulator/day_context.py` — under_bolus_factor values, carb ranges
- `app/simulator/patient_factory.py` — meal_rise_factor values

## Acceptance Criteria
- [ ] post_meal_spike: max < 280, lunch spike to 200-240, 0% ceiling
- [ ] brittle: max < 350, <5% at ceiling, clearly distinct from well_controlled
- [ ] All 180+ tests pass