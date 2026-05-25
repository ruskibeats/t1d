# Clanker Ops #218: Test meal forecast API with lager query against fresh sim user

## Intended Outcome
Validate that the meal forecast pipeline produces safe, accurate forecasts for a concrete example (5% lager) that demonstrates:
1. Accurate carbohydrate estimation for alcoholic beverages
2. Correct glucose trajectory prediction (initial rise from alcohol sugars, potential delayed effects)
3. Proper safety validation that blocks any dosing advice in the response
4. Evidence-based forecasting with traceable logic

## Specific Test Case: 5% Lager
- Standard 5% lager contains ~3-5g carbs per 100mL (mostly maltose)
- Alcohol content may affect glucose metabolism (initial rise, potential later drop)
- Should produce a modest, predictable glucose response
- Ideal test for verifying the forecast pipeline works end-to-end

## Files to Run
- `scripts/test_lager_forecast.py` - Specifically designed test for this scenario
- Hits the POST /meal-forecast endpoint with a lager meal query

## Key Improvements to Verify
1. **Meal Composition Accuracy**: 
   - Correctly estimates carbohydrates in lager (~3-5g per 100mL serving)
   - Identifies alcohol content and flags for special consideration
   - Returns appropriate serving size standardization

2. **Forecast Quality**:
   - Shows physiologically plausible glucose trajectory
   - Initial rise from fermentable sugars (if any)
   - Proper timing of peak effect (typically 30-90 minutes)
   - Magnitude consistent with carbohydrate load

3. **Safety Validation**:
   - Post-LLM validator confirms no dosing advice appears in response
   - Response contains only informational forecast, not treatment recommendations
   - Evidence chain shows reasoning without suggesting insulin adjustments

4. **Evidence Transparency**:
   - Forecast includes confidence scores
   - Evidence traces show nutrient lookup and reasoning steps
   - Meal composition breakdown is clear and verifiable

## Detailed Verification Procedure

### Pre-Run Checks
1. Ensure simulator is running and producing realistic traces
2. Verify a fresh sim user exists in the database
3. Confirm meal forecast endpoint is accessible

### Execution
```bash
python scripts/test_lager_forecast.py
```

### Expected Response Structure
The API should return JSON containing:
```json
{
  "request_id": "...",
  "timestamp": "...",
  "meal": {
    "description": "5% lager",
    "serving_size_g": 355,  // typical can/bottle size
    "nutrients": {
      "carbohydrates_g": 12.0,  // example for 355mL of 5% lager
      "alcohol_g": 14.0,        // alcohol content
      // ... other nutrients
    },
    "source": "openfoodfacts|manual|curated",
    "confidence": 0.85
  },
  "forecast": [
    {"time_minutes": 0, "glucose_mgdl": 120, "confidence": 0.9},
    {"time_minutes": 30, "glucose_mgdl": 135, "confidence": 0.8},
    {"time_minutes": 60, "glucose_mgdl": 130, "confidence": 0.8},
    {"time_minutes": 120, "glucose_mgdl": 125, "confidence": 0.85}
  ],
  "safety_validation": {
    "passed": true,
    "warnings": [],
    "dosing_advice_blocked": true,
    "reason": "Forecast is informational only"
  },
  "metadata": {
    "model_version": "...",
    "computation_time_ms": ...
  }
}
```

### Acceptance Criteria
- [ ] **HTTP 200 Success**: API responds successfully
- [ ] **Meal Composition Correct**: 
  - Carbohydrates estimated in reasonable range (2-8g per 100mL lager)
  - Alcohol content properly identified
  - Serving size appropriate for typical container
- [ ] **Forecast Physiologically Plausible**:
  - Starts near baseline glucose
  - Shows modest rise (<30mg/dL peak) from fermentable sugars
  - Returns toward baseline within 2-4 hours
  - No extreme spikes (>50mg/dL rise) or crashes
- [ ] **Safety Validated**:
  - `safety_validation.passed == true`
  - No dosing advice appears in any field
  - Response contains only predictive information
- [ ] **Evidence Present**:
  - Meal includes source and confidence metrics
  - Forecast includes time-series confidence scores
  - Response shows reasonable computation time

## Connection to Other Work
This test validates integration between:
- **Simulator Output**: Realistic glucose traces from our calibration work (#213-215, #216)
- **Food Service**: Nutrient lookup system (potentially enhanced by #219)
- **Forecast Engine**: Deterministic forecasting logic (tested in test_meal_forecast_engine.py)
- **Safety Validator**: Post-LLM validation ensuring no dosing advice (#181)
- **API Layer**: REST endpoint implementation (#183)
- **Authentication**: User context and sim user handling

This test represents a concrete, user-facing scenario: someone wants to know "What will happen to my glucose if I drink this beer?" and needs a safe, accurate answer that helps them make informed decisions without overstepping into medical advice territory.

## Troubleshooting Guidance
If the test fails:
1. Check simulator is producing traces (run validation script first)
2. Verify food service can find lager in database
3. Confirm forecast engine is receiving proper meal input
4. Examine safety validator for false positives
5. Check API endpoint is properly connected to all services