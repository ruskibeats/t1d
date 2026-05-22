---
name: "debug-sim-detector-date-range"
description: "Diagnose simulator detector zero detections caused by date range mismatch between simulated data dates and detector query window"
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
## When to Use

When PatternService detectors report 0 true positives despite valid simulated glucose data containing the expected patterns (lows, spikes, etc.).

## Procedure

1. **Verify ground truth exists in simulated data**
   ```sql
   SELECT window_start, window_end, expected_value_min, 
          COUNT(*) as reading_count, 
          MIN(value) as actual_min
   FROM sim_hidden_truths th
   JOIN health_metrics hm ON hm.user_id = th.real_user_id
   WHERE hm.measured_at BETWEEN th.window_start AND th.window_end
   GROUP BY th.id, th.window_start, th.window_end, th.expected_value_min;
   ```

2. **Check date range mismatch**
   ```sql
   -- Simulated data range
   SELECT MIN(measured_at), MAX(measured_at) FROM health_metrics 
   WHERE source = 'simulator';
   
   -- Detector query range (typically "now - 365 days")
   SELECT 
     (datetime '2026-05-21' - INTERVAL '365 days') as detector_start,
     datetime '2026-05-21' as detector_end;
   ```

3. **Confirm zero detector edges created**
   ```sql
   SELECT COUNT(*) as total_edges, 
          COUNT(DISTINCT edge_type) as distinct_types 
   FROM health_metric_edges;
   ```

4. **The fix**: In `_run_detectors()`, use simulation dates instead of wall-clock dates
   ```python
   # BEFORE (broken)
   start_date = datetime.now() - timedelta(days=365)
   end_date = datetime.now()
   
   # AFTER (fixed)
   start_date = sim_date_start  # from base_date in orchestrator
   end_date = sim_date_start + timedelta(days=run.days_per_user + 2)
   ```

## Pitfalls

- Don't confuse `created_at` on edges with the actual metric timestamp
- Window alignment checks must use overlap calculation, not just start/end comparison
- Simulator data in Jan 2025 queried against "past 365 days from May 2026" = zero overlap

## Verification

After fix, `health_metric_edges` should have rows and detector scores should show non-zero recall/precision.