# Calibration Protocol

How to measure forecast quality against real Nightscout data.

## Data Requirements

### Inclusion Rules
- Meal events: >30g carb equivalent (heuristic: rise >20 mg/dL in 1 hour)
- Valid CGM: No ??? states, <3 consecutive missing readings
- Time window: Meals within 4 hours of CGM trace available

### Exclusion Rules  
- Hypo treatments within 2 hours before meal
- Exercise flags or temp targets active
- Sensor change or calibration within 1 hour
- Meals logged >30 min after glucose rise detected

## Metrics

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Peak error | <20 mg/dL | >30 mg/dL |
| Time error | <30 min | >60 min |
| MAE (hourly) | <15 mg/dL | >25 mg/dL |
| Drift rate | <5% per month | >10% triggers review |

## Calibration Process

1. **Export**: Nightscout CSV or Dexcom API dump
2. **Parse**: `calibration_harness.load_nightscout_*()`
3. **Identify**: `find_meal_events(epochs)` 
4. **Compare**: `compare_forecast_to_trace(result, meal)`
5. **Summarize**: `summarize_calibration_results(suite_results)`
6. **Trigger**: If drift >15%, emit calibration_alert

## Files

- `demo/calibration_harness.py` - Implementation
- `docs/fixtures/sample_meal.csv` - Test fixture
- `docs/state_serialization_spec.md` - State boundaries