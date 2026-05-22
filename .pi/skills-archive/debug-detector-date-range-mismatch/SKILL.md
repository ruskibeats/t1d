---
name: "debug-detector-date-range-mismatch"
description: "Debug pattern detector failures caused by date range mismatches between simulated data and detector query windows"
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

- Detector returns zero detections despite valid input data
- Simulated/historical data ranges don't match detection query windows
- Time-series pattern matching fails unexpectedly

## Procedure

### 1. Compare Data Ranges
```sql
-- Check simulated data date range
SELECT MIN(measured_at), MAX(measured_at) FROM health_metrics WHERE source = 'simulator';

-- Check detector date window (if hardcoded)
-- Example: detector using `NOW() - INTERVAL '365 days'`
SELECT (NOW() - INTERVAL '365 days') AS start_date, NOW() AS end_date;
```

### 2. Verify Overlap
```sql
WITH sim_range AS (SELECT MIN(measured_at) AS start, MAX(measured_at) AS end FROM health_metrics WHERE source = 'simulator'),
detector_range AS (SELECT NOW() - INTERVAL '365 days' AS start, NOW() AS end)
SELECT 
  sim_range.start < detector_range.end AS has_overlap_low,
  detector_range.start < sim_range.end AS has_overlap_high;
```

### 3. Fix Implementation
```python
# In simulator service:
# BEFORE: start_date = datetime.now() - timedelta(days=365)
# AFTER: start_date = sim_date_start (passed from simulation context)
#        end_date = sim_date_start + timedelta(days=sim_days_per_user)
```

### 4. Add Regression Test
```python
def test_detector_uses_simulated_date_range():
    # Arrange: create data for specific past dates
    # Act: run detector
    # Assert: detections occur in expected window
    pass
```

## Pitfalls to Avoid

1. **Hardcoded "now" in queries** - Always use data-relative dates for simulations
2. **Assuming date alignment** - Explicitly verify ranges match before debugging detection logic
3. **Not flushing transactions** - Simulator runs need `await db.commit()` before evaluation

## Verification

- Run small cohort (5 patients, 7 days)
- Check that `sim_detector_scores` has non-zero detections
- Verify `health_metric_edges` has created edges matching ground truth