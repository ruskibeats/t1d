---
name: "calibration-sparse-bin-protection"
description: "Protect confidence calibration analysis against sparse bins that distort Expected Calibration Error (ECE). Auto-merge low-sample bins into nearest neighbors, enforce min-sample floor for threshold recommendations, and report which bins were collapsed. Use when calibrating detector confidence scores from limited evaluation samples."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Calibration Sparse Bin Protection

## When to Use

You compute calibration curves (binned empirical accuracy vs. predicted confidence) from detector/classifier outputs but have limited evaluation samples. Sparse bins — those with only 1-4 samples — produce unreliable ECE contributions and dangerously overconfident threshold recommendations.

Use when:
- Computing Expected Calibration Error (ECE) from fewer than ~500 (confidence, is_correct) pairs
- Generating deployment threshold recommendations from calibration curves
- Bin-level breakdowns where some bins naturally have low support (e.g., <10% confidence bin in a well-calibrated detector)

Do NOT use when:
- You have thousands of samples evenly distributed across all confidence bins (10+ per bin)
- You're doing binary calibration without binning (e.g., Platt scaling, isotonic regression)

## Procedure

### 1. Create a CalibrationBin class

Each bin stores its confidence range, all samples (confidence + correctness), and computes summary statistics:

```python
class CalibrationBin:
    def __init__(self, bin_index: int, bin_lower: float, bin_upper: float):
        self.bin_index = bin_index
        self.bin_lower = bin_lower
        self.bin_upper = bin_upper
        self.confidences: list[float] = []
        self.is_correct: list[bool] = []

    def add(self, confidence: float, correct: bool) -> None:
        self.confidences.append(confidence)
        self.is_correct.append(correct)

    @property
    def support(self) -> int:
        return len(self.confidences)

    @property
    def avg_confidence(self) -> float:
        return mean(self.confidences) if self.confidences else 0.0

    @property
    def empirical_accuracy(self) -> float:
        return mean(self.is_correct) if self.is_correct else 0.0

    @property
    def calibration_error(self) -> float:
        return abs(self.avg_confidence - self.empirical_accuracy)
```

### 2. Define Constants

```python
DEFAULT_BIN_COUNT = 10            # 0-0.1, 0.1-0.2, ..., 0.9-1.0
MIN_SAMPLES_PER_BIN = 5           # minimum support for a "reliable" bin
MIN_THRESHOLD_SAMPLES = 10        # minimum samples above threshold for a recommendation
DEPLOYMENT_ACCURACY_TARGET = 0.80 # minimum accuracy for deployed edges
```

### 3. Assign Samples to Bins

```python
def assign_to_bins(pairs, bin_count=DEFAULT_BIN_COUNT):
    """Assign (confidence, is_correct) pairs to equally-spaced bins."""
    bins = [
        CalibrationBin(i, i / bin_count, (i + 1) / bin_count)
        for i in range(bin_count)
    ]
    for confidence, correct in pairs:
        confidence = max(0.0, min(0.999, confidence))  # clamp
        bin_idx = min(int(confidence * bin_count), bin_count - 1)
        bins[bin_idx].add(confidence, correct)
    return bins
```

### 4. Auto-Merge Sparse Bins Into Nearest Neighbor

This is the core protection. Bins with fewer than `MIN_SAMPLES_PER_BIN` samples are unreliable — a bin with 1 sample showing 100% accuracy would distort ECE dramatically.

```python
def merge_sparse_bins(populated_bins):
    """Merge bins with < MIN_SAMPLES_PER_BIN into nearest populated neighbor."""
    if len(populated_bins) <= 1:
        return populated_bins

    populated_bins.sort(key=lambda b: b.bin_index)
    sparse_indices = {b.bin_index for b in populated_bins 
                      if b.support < MIN_SAMPLES_PER_BIN}
    
    if not sparse_indices:
        return populated_bins
    
    dense = [b for b in populated_bins if b.bin_index not in sparse_indices]
    if not dense:
        # All bins are sparse — return as-is (no reliable data)
        return populated_bins
    
    for b in populated_bins:
        if b.bin_index in sparse_indices:
            nearest = min(dense, key=lambda db: abs(db.bin_index - b.bin_index))
            for conf, correct in zip(b.confidences, b.is_correct):
                nearest.add(conf, correct)
    
    return dense
```

**Why nearest-neighbor merging?**:
- Assumes adjacent confidence ranges have similar calibration properties
- Preserves the overall calibration curve shape better than dropping sparse bins
- The merged bin's accuracy is diluted proportionally (the dense bin's samples dominate, which is correct — they're more reliable)

### 5. Compute ECE From Merged Bins

```python
def compute_ece(bins, total_samples):
    """ECE = sum_b (n_b / N) * |acc_b - conf_b|"""
    if total_samples == 0:
        return 0.0
    return sum(
        (b.support / total_samples) * b.calibration_error
        for b in bins
    )
```

### 6. Find Threshold With Min-Samples Guard

This prevents recommending a confidence threshold based on 1-2 samples:

```python
def find_threshold(calibration_result, accuracy_target=0.80, min_samples=10):
    """Find minimum confidence achieving target accuracy with min_samples guard."""
    if calibration_result.total_samples < min_samples:
        return None  # too few samples for any recommendation
    
    # Build (confidence, is_correct) pairs sorted descending
    pairs = sorted(
        [(c, ok) for b in calibration_result.bins 
         for c, ok in zip(b.confidences, b.is_correct)],
        key=lambda x: x[0],
        reverse=True
    )
    
    # Scan from high to low confidence
    best = None
    prefix_correct = 0
    for i, (conf, correct) in enumerate(pairs):
        prefix_correct += int(correct)
        accuracy = prefix_correct / (i + 1)
        if accuracy >= accuracy_target and (i + 1) >= min_samples:
            best = (conf, accuracy, i + 1)
        else:
            break  # accuracy dropped below target
    
    if best is None:
        return None
    
    return {
        "min_confidence": round(best[0], 3),
        "expected_accuracy": round(best[1], 3),
        "samples_above_threshold": best[2],
        "total_samples": len(pairs),
        "recall_at_threshold": round(best[2] / len(pairs), 3),
    }
```

**Why this works**: By scanning from high confidence downward, the first time accuracy drops below target, we stop — the previous confidence was the lowest valid threshold. The `min_samples` guard ensures we don't recommend a threshold based on a single lucky prediction.

### 7. Report Which Bins Were Merged

Always keep raw bins for transparency, but report merged indices:

```python
class CalibrationResult:
    def __init__(self, label, bins, min_samples_per_bin=5):
        self.label = label
        self.raw_bins = list(bins)
        self.bins = merge_sparse_bins([b for b in bins if b.support > 0])
        self.merged_bin_indices = [
            b.bin_index for b in bins
            if b.support > 0 and b.support < min_samples_per_bin
        ]
    
    def to_dict(self):
        return {
            "label": self.label,
            "ece": round(self.ece, 4),
            "bins": [b.to_dict() for b in self.bins],
            "raw_bins": [b.to_dict() for b in self.raw_bins if b.support > 0],
            "merged_bin_indices": self.merged_bin_indices,
            "threshold": self.find_threshold(),
        }
```

## Pitfalls

### Sparse bins distort ECE even with just 1-2 samples
A bin with `avg_confidence=0.95, empirical_accuracy=1.0` (1 sample) has error=0.05. Weighted by support (1/N), that seems small. But if that bin represents a meaningful mode (e.g., all edge cases concentrate at 0.95 confidence), merging it loses information. Mitigation: always inspect `merged_bin_indices` to see which regions were collapsed.

### All bins are sparse (no reliable data)
If every bin has <MIN_SAMPLES_PER_BIN samples, no calibration is reliable. Return the result as-is but set `ece=None` and skip threshold recommendations. The proper response is "insufficient data" not "ECE=0.0".

### Empty high-confidence bins
If your detector never outputs confidence > 0.9, the top bin is empty. Code that iterates bins should skip empty bins rather than treating them as 0-weight. An empty bin means "no predictions at this confidence level" — a useful signal about model behavior.

### Non-Bayesian vs Bayesian binning
This procedure uses empirical binning (simple counts). For v2, add:
- **Bayesian binning with beta prior**: adds confidence intervals around each bin's accuracy (useful for small sample sizes)
- **Pool-adjacent-violators (PAV) isotonic regression**: smooths the calibration curve by merging adjacent bins that violate monotonicity

### Threshold scanning direction matters
Always scan from **high confidence downward**. Scanning from low to high would find the first confidence where accuracy *dips below target* — the *highest* valid threshold, which is maximally exclusive (rejects many true positives). Scanning from high to low finds the *lowest* valid threshold, which is maximally inclusive while still meeting the accuracy target.

## Verification

```python
# Test 1: No sparse bins → no merging
pairs = [(0.1, True)] * 6 + [(0.9, True)] * 10  # 6 in bin 1, 10 in bin 9
bins = assign_to_bins(pairs, bin_count=10)
result = CalibrationResult("test", bins)
assert len(result.merged_bin_indices) == 0, "Should not merge with >=5 per bin"
assert result.ece > 0, "Should have non-zero ECE"

# Test 2: Sparse bin gets merged
pairs = [(0.1, True)] * 6 + [(0.15, True)] * 2 + [(0.9, True)] * 10
# bin 1 (0.1-0.2) has 8 samples total, bin 0 has 0
bins = assign_to_bins(pairs, bin_count=10)
result = CalibrationResult("test", bins)
# The 2 samples at 0.15 fall into bin 1, which already has 6 from bin 0.1
# Actually bin 0.1 → idx 1 (0.1*10=1), bin 0.15 → idx 1 too
# So all 8 go to bin 1. No sparse bins.
# Let me use a more targeted test:
pairs2 = [(0.05, True)] * 2 + [(0.95, True)] * 10  # bin 0 sparse (2), bin 9 dense (10)
bins2 = assign_to_bins(pairs2, bin_count=10)
result2 = CalibrationResult("test", bins2)
assert 0 in result2.merged_bin_indices, "Bin 0 should be merged"
assert result2.ece >= 0, "ECE should be computable"

# Test 3: Threshold requires min_samples
pairs3 = [(0.99, True)] * 5  # only 5 samples, all correct
bins3 = assign_to_bins(pairs3, bin_count=10)
result3 = CalibrationResult("test", bins3)
assert result3.find_threshold(min_samples=10) is None, "Should reject <10 samples"
assert result3.find_threshold(min_samples=5) is not None, "Should accept >=5 samples"

# Test 4: All sparse → no threshold recommendation
pairs4 = [(0.5, True)] * 3 + [(0.6, False)] * 2  # all < 5 per bin
bins4 = assign_to_bins(pairs4, bin_count=10)
result4 = CalibrationResult("test", bins4)
assert result4.find_threshold() is None, "Should not recommend threshold from sparse data"

# Test 5: to_dict includes merged_bin_indices and raw_bins
d = result2.to_dict()
assert "merged_bin_indices" in d
assert "raw_bins" in d
assert len(d["raw_bins"]) >= len(d["bins"]), "raw_bins should include all populated bins"
```

## Boundary Conditions

- **Should use**: Any confidence calibration with bin-count < 5× the number of bins (e.g., <50 samples for 10 bins)
- **Should use**: When generating deployment threshold recommendations from calibration curves
- **Do NOT use**: For probability calibration methods that don't use binning (Platt scaling, beta calibration, isotonic regression on individual samples)
- **Do NOT use**: When you have 5000+ well-distributed samples and bin counts of 10 — sparse bins won't occur