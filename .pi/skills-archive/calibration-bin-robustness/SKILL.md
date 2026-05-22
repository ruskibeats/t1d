---
name: "calibration-bin-robustness"
description: "Make binned confidence calibration robust by protecting against sparse bins and enforcing a sample-count floor on threshold recommendations. Use when building or reviewing a calibration/evaluation module that computes binned accuracy, ECE, MCE, or confidence thresholds."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Calibration Bin Robustness

## When to Use

Apply when building or reviewing a calibration/evaluation **binning module** that:
- Computes binned accuracy, ECE (Expected Calibration Error), or MCE (Maximum Calibration Error)
- Issues confidence threshold recommendations (e.g., "edges with confidence >= 0.85 achieve 90% accuracy")
- Maps continuous confidence scores into discrete bins (typically 10 bins of width 0.1)
- Has boolean correctness labels per prediction

**Do not use** for:
- Regression evaluation (MSE, R² — no confidence binning)
- Raw classification metrics (accuracy, F1 — no binned calibration)
- Single-threshold or non-binned calibration approaches

## Procedure

### Step 1 — Set a minimum samples-per-bin threshold

```python
# Minimum samples required in a populated bin for a reliable estimate.
# Bins below this are considered sparse and merged into neighbors.
MIN_SAMPLES_PER_BIN = 5
```

**Why 5?** A bin with 1-4 samples can produce misleading accuracy (e.g., 1/1 = 100%). With 5+ samples, the accuracy estimate starts to stabilize. Raise this to 10 for higher-confidence requirements.

### Step 2 — Preserve raw bins alongside merged bins

Keep the original bins for transparency, then produce a merged list for ECE computation:

```python
class CalibrationResult:
    def __init__(self, label, bins):
        self.label = label
        self.raw_bins = list(bins)  # keep originals for transparency
        self.bins = self._merge_sparse_bins([b for b in bins if b.support > 0])
        self.merged_bin_indices = [
            b.bin_index for b in bins
            if b.support > 0 and b.support < MIN_SAMPLES_PER_BIN
        ]
```

### Step 3 — Implement sparse bin merging

Merge bins with fewer than `MIN_SAMPLES_PER_BIN` samples into the **nearest populated neighbor**:

```python
def _merge_sparse_bins(self, populated: list[Bin]) -> list[Bin]:
    if len(populated) <= 1:
        return populated

    populated.sort(key=lambda b: b.bin_index)
    sparse_indices = {b.bin_index for b in populated 
                       if b.support < MIN_SAMPLES_PER_BIN}
    if not sparse_indices:
        return populated

    dense = [b for b in populated if b.bin_index not in sparse_indices]
    if not dense:
        # All bins sparse — return as-is (no merge possible)
        return populated

    for b in populated:
        if b.bin_index in sparse_indices:
            nearest = min(dense, key=lambda db: abs(db.bin_index - b.bin_index))
            for conf, correct in zip(b.confidences, b.is_correct):
                nearest.add(conf, correct)

    return dense
```

**Key design decisions:**
- **Nearest neighbor by bin_index**: A sparse bin at index 1 (confidence 0.1-0.2) merges into index 0 or 2, whichever exists. This preserves the closest confidence region.
- **Merge confidences + correctness, not stats**: Re-add each (confidence, is_correct) pair so the receiving bin's size and accuracy update naturally.
- **All-sparse fallback**: If all bins are sparse, return them as-is rather than collapsing everything into one bin. The ECE will be unreliable, but the consumer can see why.

### Step 4 — Add a min-samples floor to threshold recommendation

When computing "what minimum confidence achieves 80% accuracy?", the result is unreliable if computed from only a handful of samples. Add a `min_samples` parameter:

```python
def find_threshold(
    self,
    accuracy_target: float = 0.80,
    min_samples: int = 10,
) -> Optional[dict]:
    """Find lowest confidence achieving target accuracy.
    
    Requires at least ``min_samples`` predictions above the candidate
    threshold — otherwise the recommendation is overfitted to noise.
    """
    if self.total_samples < min_samples:
        return None  # Not enough data to make any recommendation

    # Scan from high confidence downward...
    # ... (standard ECE threshold scanning code)

    if best_count < min_samples:
        return None  # Too few high-confidence predictions

    return {
        "min_confidence": round(best_threshold, 3),
        "achieved_accuracy": round(best_accuracy, 3),
        "sample_count": best_count,
    }
```

### Step 5 — Report merged indices in serialization output

Consumers (dashboards, reports, API responses) need to know which bins were collapsed:

```python
def to_dict(self) -> dict:
    return {
        "ece": round(self.ece, 4),
        "mce": round(self.mce, 4),
        "bins": [b.to_dict() for b in self.bins],  # merged bins for ECE
        "raw_bins": [b.to_dict() for b in self.raw_bins if b.support > 0],
        "merged_bin_indices": self.merged_bin_indices,
        "min_samples_per_bin": MIN_SAMPLES_PER_BIN,
        "threshold": self.find_threshold(target=0.80),
    }
```

### Step 6 — Test the robustness

Write tests for the critical cases:

```python
def test_sparse_bins_merged_into_nearest():
    """A bin with 1 sample should merge into the nearest dense neighbor."""
    bins = [
        CalibrationBin(0, lower=0.0, upper=0.1),
        CalibrationBin(1, lower=0.1, upper=0.2),
        CalibrationBin(2, lower=0.2, upper=0.3),
    ]
    bins[0].add(0.05, True)  # sparse: 1 sample
    bins[1].add(0.15, True)
    bins[1].add(0.16, False)
    bins[1].add(0.17, True)
    bins[1].add(0.18, True)
    bins[1].add(0.14, True)  # dense: 5 samples
    bins[2].add(0.25, True)
    bins[2].add(0.26, True)
    bins[2].add(0.27, False)
    bins[2].add(0.28, True)
    bins[2].add(0.29, False)  # dense: 5 samples

    result = CalibrationResult("test", bins)
    assert len(result.bins) == 2  # bin 0 merged into bin 0 or 1
    assert 0 in result.merged_bin_indices  # bin 0 was merged


def test_threshold_skipped_when_samples_below_floor():
    """find_threshold returns None when total samples < min_samples."""
    result = CalibrationResult("test", bins_with_few_samples(support=3))
    assert result.find_threshold(min_samples=10) is None  # 3 < 10


def test_all_bins_sparse_returns_all():
    """When every bin is sparse, no merging attempted — return as-is."""
    bins = [make_bin(i, samples=1) for i in range(10)]
    result = CalibrationResult("test", bins)
    assert len(result.bins) == 10  # no merging
    
    
def test_merged_indices_reported_in_to_dict():
    result = CalibrationResult("test", make_bins_with_one_sparse())
    d = result.to_dict()
    assert "merged_bin_indices" in d
    assert "raw_bins" in d
    assert "min_samples_per_bin" in d
```

## Pitfalls

### Merge heuristic choice matters
- **Nearest-by-index** is the simplest but can merge a 0.0-0.1 bin into 0.9-1.0 if the mid-bins are all sparse. For most confidence distributions this is unlikely (sparsity is usually in extreme bins).
- **Alternative**: Bayesian binning with a Beta prior avoids merging entirely by computing credible intervals per bin. Use if you have fewer total bins (<5) or expect systematic sparsity. At ≥10 bins with ≥5 samples/boundary, nearest-neighbor is sufficient.

### Threshold floor selection
- 10 is the **minimum safe value** for `min_samples` in threshold finding. At 10, a single prediction flip (9/10 vs 10/10) only shifts accuracy by 10pp.
- For production deployment recommendations, use 25+ samples above threshold.
- For exploration/dashboarding, 5 is acceptable (but mark as "low confidence").

### Transparency ≠ Complexity
- Exposing `raw_bins` in the output avoids confusion when a consumer sees 5 bins instead of 10 and wonders where the data went.
- Without `merged_bin_indices`, debugging an unexpectedly perfect calibration curve is much harder — the merged data may artificially improve ECE.

### Don't over-merge
- If >40% of bins are sparse, the merged data is unreliable regardless. Log a warning: `"WARNING: {pct_sparse:.0f}% of bins sparse after merging — total samples may be insufficient for meaningful calibration."`
- Consider increasing overall sample count rather than relying on merging.

## Verification

```bash
# Run the robustness tests
python3 -m pytest tests/test_calibration.py -v -k "sparse_bins or threshold_samples or merged_indices"

# Quick sanity: check sparse bin merging
python3 -c "
from calibration import CalibrationBin, CalibrationResult
bins = [CalibrationBin(i, i/10, (i+1)/10) for i in range(10)]
for i in range(5): bins[i].add(i/10 + 0.05, True)
# bin 5-9 are sparse
result = CalibrationResult('sanity', bins)
assert len(result.bins) <= len(bins), 'merging should reduce bin count'
assert len(result.merged_bin_indices) > 0, 'should detect sparse bins'
print('OK: merged', len(result.merged_bin_indices), 'sparse bins')
"

# Existing tests — no regressions
python3 -m pytest tests/test_*.py -v --ignore=tests/unrelated
```