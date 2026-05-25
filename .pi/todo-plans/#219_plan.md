# Clanker Ops #219: Improve food search quality — OFF ranking, manual entry, curated staples

## Intended Outcome
Achieve reliable, high-confidence food search that eliminates embarrassing mismatches like "fried eggs" → gummy candy. Implement a multi-path resolution system with appropriate fallback and confidence scoring that supports accurate meal logging and forecasting.

## Current Problem & Root Cause
Open Food Facts (OFF) returns low-confidence matches due to:
1. **Poor ranking algorithm**: Exact matches not prioritized
2. **Incomplete data**: Missing nutrients for many entries
3. **No manual override**: Users can't correct obvious errors
4. **No curated fallbacks**: Common foods not prioritized
5. **Weak confidence scoring**: No nuanced quality assessment

## Solution Architecture: Multi-Path Resolution with Confidence Scoring
Implement a 4-tier fallback system:
```
Tier 1: Barcode lookup → Exact OFF match (highest confidence)
Tier 2: Branded search → OFF with brand preference boosting  
Tier 3: Generic search → OFF with nutrient completeness scoring
Tier 4: Manual entry → User-defined or curated staple (verified)
```

## Files to Modify
- `app/food/service.py` - Main search logic and fallback implementation
- `app/food/provenance.py` - Confidence scoring, source tracking, nutrient standardization
- `app/food/schemas.py` - Data models for enhanced food items
- `app/api/food.py` - Endpoint updates for manual entry
- `app/db/models.py` - Potential new tables for curated staples/manual foods

## Detailed Implementation Plan

### Phase 1: Enhanced Search Service (app/food/service.py)
1. **Search Priority Refinement**:
   - Exact name match boost (+0.3 confidence)
   - Brand preference scoring (user history + common brands)
   - Nutrient completeness scoring (% of macros present)
   - Serving unit standardization (all to per-100g basis)

2. **Multi-Stage Query Processing**:
   ```
   Query → [Barcode Check] → [OFF Search w/ Enhanced Ranking] 
         → [Curated Staples Check] → [Manual Foods Check] 
         → [Guided Creation Prompt]
   ```

### Phase 2: Confidence Scoring System (app/food/provenance.py)
1. **Confidence Components** (0.0-1.0 scale):
   - **Source Trust** (0.4 weight): Barcode > Branded OFF > Generic OFF > Manual
   - **Match Quality** (0.3 weight): Exact/fuzzy match score, brand alignment
   - **Data Completeness** (0.2 weight): % of expected nutrients present
   - **Recency/Usage** (0.1 weight): User-specific boost for frequently used

2. **Confidence Thresholds**:
   - ≥0.8: High confidence (auto-accept)
   - 0.6-0.79: Medium confidence (show alternatives)  
   - <0.6: Low confidence (require manual verification)

### Phase 3: Curated Staples Database
Create verified entries for common foods:
- Proteins: eggs, chicken breast, beef, tofu, fish
- Carbs: rice, pasta, bread, potatoes, oats, fruits
- Fats: oils, nuts, avocado, cheese
- Beverages: water, coffee, tea, beer, wine, soda
- Mixed meals: sandwich, salad, burger (template versions)

### Phase 4: Manual Food Entry System
Allow users to:
1. Enter food name and serving size
2. Input macros directly (carbs, protein, fat, calories)
3. Optionally add ingredients for auto-calculation
4. Save to personal food library for reuse
5. Share with care team if desired

### Phase 5: Serving Standardization & Comparison
- Convert all foods to standardized per-100g basis for fair comparison
- Implement unit conversion (g, ml, oz, cups, pieces, slices)
- Enable nutrient density scoring for search ranking

## Acceptance Criteria
- [ ] Search for "fried eggs" returns egg-based foods first (not candy)
- [ ] Barcode search works reliably for packaged goods with >90% success rate
- [ ] Manual entry allows creating foods with custom macro nutrients
- [ ] Curated staples provide instant results for 50+ common foods
- [ ] Confidence scores appropriately reflect match quality (test with known good/bad cases)
- [ ] All food-related tests pass (test_food_quality.py etc.)
- [ ] No regression in existing food search or nutrient calculation
- [ ] Response includes source transparency and confidence metrics

## Connection to Other Work
This improves the foundation for:
- **Meal Forecasting**: Accurate carb estimation → better glucose predictions
- **Food Logging**: Reduced user frustration, increased adherence
- **Nutrient Tracking**: Complete macro/micro nutrient data for trends
- **Pattern Detection**: Accurate meal representation in simulation improves pattern detection
- **Safety Validation**: Correct meal inputs prevent dangerous forecasting errors
- **Clinical Decision Support**: Reliable data for care team recommendations

This addresses the explicit user requirement for "multi-path resolution: barcode → branded → generic → manual entry" and the observed problem of "food search returns non-food matches (e.g., 'fried eggs' → gummy candy)".