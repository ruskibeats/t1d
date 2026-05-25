# [CAL] Calibrate Simulator Anchors from HUPA-UCM Dataset

## Intended Outcome
Simulator anchors are calibrated to real-world T1D physiology from HUPA-UCM public dataset, enabling clinically grounded synthetic data generation.

## Step-by-Step Plan

### Phase 1: Dataset Acquisition
1. Download HUPA-UCM dataset from Mendeley (public access)
2. Extract and parse CSV structure
3. Load into working directory: `./data/hupa-ucm/`

### Phase 2: Data Normalization
1. Convert timestamps to UTC
2. Normalize patient IDs
3. Handle missing CGM values (<15min gaps: forward fill, longer: mark as missing)

### Phase 3: Feature Extraction (per patient)
- TIR 70-180 mg/dL
- Overnight hypo rate (0-6 AM)
- Postprandial spike frequency (>200 mg/dL within 2 hrs of carbs)
- Variability (CV of glucose)
- Hypo correction rate
- Dawn phenomenon detection

### Phase 4: Unsupervised Clustering
- Apply K-means (k=12) on feature matrix
- Validate cluster stability

### Phase 5: Anchor Mapping
- Map clusters to 12 anchor names based on dominant phenotype
- Handle mixed-pattern patients via ensemble assignment

### Phase 6: Parameter Derivation
Derive per-anchor parameters:
- basal_glucose_mean / amplitude
- meal_rise_factor (mg/dL per gram carb)
- insulin_sensitivity
- carb_ratio
- hypo_risk
- noise_sd
- exercise_drop_factor
- dawn_effect_strength
- fat_delay_hours
- variability_cv

### Phase 7: Gap Resolution
- Identify missing anchor coverage
- Interpolate from similar anchors
- Use literature defaults for edge cases (citations in report)

### Phase 8: Validation
- Cross-check parameters against:
  - CGM variability literature
  - Insulin sensitivity ranges from diabetes tech studies
  - Meal response durations from clinical nutrition papers

## Files to Create
```
calibration/
├── hupa_ucm_parser.py          # Download + parse
├── feature_extractor.py        # Extract phenotype features
├── cluster_anchors.py          # K-means clustering
├── calibrate_parameters.py     # Derive anchor params
├── interpolate_gaps.py         # Handle missing anchors
└── calibrated_anchors.json     # Final output
```

## Verification
```bash
# Run calibration pipeline
python calibration/hupa_ucm_parser.py
python calibration/feature_extractor.py  
python calibration/cluster_anchors.py
python calibration/calibrate_parameters.py

# Check output
test -f calibration/calibrated_anchors.json && echo "OK" || echo "FAIL"
```

## Audit (EOD Report-Back)
Append to .pi/EOD_AUDIT.md:
1. Files created/modified (list with paths)
2. Number of patients successfully processed
3. Anchors mapped vs gaps identified
4. Interpolation decisions documented
5. Estimated tokens: