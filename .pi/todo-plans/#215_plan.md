# Clanker Ops #215: Batch-calibrate remaining 8 anchors

## Intended Outcome
All 12 anchors produce clinically plausible glucose traces. The 8 new anchors (dawn_phenomenon, exercise_regimen, high_fat_delayed, high_variability, insulin_resistant, insulin_sensitive, exercise_sensitive, newly_diagnosed) should each have distinct, named characteristics that stress-test the pattern detectors in different ways.

## Blocked By
This task is blocked by #213 (cumulative drift fix) and #214 (post_meal_spike/brittle calibration). Don't start until both are verified.

## Anchor Specs

### dawn_phenomenon
- Range: 80-200, TIR >65%
- Morning rise: waking ~130, rises to ~180-220 by 7-9AM, then returns to baseline
- Other meals: near well_controlled
- Distinct feature: early morning elevation that other anchors don't show

### exercise_regimen
- Range: 70-230, TIR >60%  
- Exercise: min 4 days/week with visible glucose drops (30-50 mg/dL below baseline)
- Meals: near well_controlled but with more post-exercise recovery lows

### high_fat_delayed
- Range: 80-250, TIR >50%
- Delayed spike: 1-2 meals with high fat cause a second glucose peak 3-5h after eating
- Identifiable by: biphasic meal response (initial rise, partial recovery, second rise)

### high_variability
- Range: 50-350, TIR ~30-40%
- Wide swings with irregular pattern
- Less extreme than brittle but clearly unstable
- Both hypo and hyper excursions

### insulin_resistant
- Range: 100-300, TIR ~30-40%
- Higher overall mean (~180-220)
- Sluggish response to insulin — meals take longer to recover
- Higher basal glucose mean

### insulin_sensitive
- Range: 60-180, TIR >75%
- Lower overall mean (~100-130)
- Sharp drops after insulin — caution with hypo
- Similar to well_controlled but tighter

### exercise_sensitive
- Range: 60-250, TIR >50%
- Exercise causes more dramatic glucose drops (40-80 mg/dL below baseline)
- May need to reduce bolus on exercise days

### newly_diagnosed
- Range: 80-350, TIR ~20-30%
- Higher variability, less consistent dosing
- Learning phase — meals and insulin not well matched
- More excursions in both directions than any other anchor

## Approach
For each anchor, apply the same pattern as well_controlled but with anchor-specific parameters:
1. Set meal_rise_factor in patient_factory.py
2. Set carb ranges in day_context.py CARBS dict
3. Set under_bolus_factor in day_context.py _generate_insulin
4. Set exercise frequency in day_context.py _generate_exercise
5. Set basal_glucose_mean in the AnchorParameterRange (schemas.py or anchors.py)
6. Run calibration test and verify against spec
7. Add any anchor-specific event generation logic if needed (e.g., high_fat_delayed needs is_high_fat flag on meals)

## Verification
Run the calibration test for all 8 anchors. Expected: each anchor has visually distinct trace, all are clinically plausible, none have >5% ceiling saturation, none have >20% severe hypo (<54).

## Acceptance Criteria
- [ ] All 12 anchors produce traces that are visually distinct from each other
- [ ] No anchor has >5% of readings at ceiling
- [ ] No anchor has >20% of readings below 54 (unless explicitly designed for it)
- [ ] All 180+ tests pass
- [ ] Calibration verified with 2 different seeds per anchor