# Golden Test Matrix

Coverage requirements for Phase 3 integration.

## Profile Matrix (12 profiles)

| Anchor | Carbs | Sugars | Fat | Expected Behavior |
|--------|-------|--------|-----|-------------------|
| well_controlled | 40-60g | 10-20g | <10g | Standard 1-2h peak |
| high_fat_delayed | 40-80g | 10-20g | >25g | Delayed peak (3-4h) |
| post_meal_spike | 30-50g | >25g | <15g | Rapid spike, early peak |
| brittle | 30-60g | variable | variable | Variable timing, high error |
| dawn_phenomenon | Any | Any | Any | Baseline rise pattern |
| overnight_hypo | Any | Any | Any | Careful low handling |
| exercise_sensitive | 30-50g | variable | <10g | Reduced rise (heat mod) |
| exercise_regimen | Any | Any | Any | Timing-sensitive |
| insulin_sensitive | 30-50g | variable | variable | Higher rise per carb |
| insulin_resistant | 50-100g | variable | variable | Lower rise per carb |
| high_variability | Any | Any | Any | Wide variance |
| newly_diagnosed | Any | Any | Any | Higher variability |

## Meal Archetype Matrix

| Meal | Carbs | Sugars | Fat | Protein | Test Focus |
|------|-------|--------|-----|---------|------------|
| Pizza | 60-80g | 20-30g | 25-40g | 20-30g | Fat delay, extended tail |
| Cereal | 30-50g | 25-40g | 2-5g | 5-10g | Fast spike, early peak |
| Pasta | 50-70g | 5-10g | 5-15g | 10-15g | Slow absorption |
| Sushi | 40-60g | 10-15g | 10-20g | 20-30g | Protein + fat combo |
| Fruit | 20-40g | 15-30g | 0-2g | 0-2g | Pure sugar spike |

## Safety Phrase Blocking

Banned words to check in all outputs:
- insulin, bolus, injection, dose, deliver
- pump, basal, TBR, temp basal
- SMB, microbolus, correction

## Demo vs Agent Parity

Tests must pass identically in:
- Standalone CLI (`python demo/companion_pipeline_v2.py "meal"`)
- Agent mode (`run_companion_pipeline()`)
- Forecast renderer output to text file