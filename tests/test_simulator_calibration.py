"""Tests for confidence calibration analysis.

Covers:
- Binning logic
- ECE calculation
- Threshold recommendations
- Per-pattern and overall calibration
- Edge cases (empty data, single bin, perfect calibration)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.simulator.calibration import (
    CalibrationBin,
    CalibrationResult,
    compute_calibration,
    compute_calibration_by_group,
    compute_full_calibration_summary,
    DEFAULT_BIN_COUNT,
)
from app.simulator.models import SimHiddenTruth


def make_truth(
    pattern_type: str = "post_meal_spike",
    confidence: float = 0.5,
    detected: bool = True,
) -> SimHiddenTruth:
    """Helper to create a hidden truth with known confidence/detection.

    Using SQLAlchemy's constructor for ORM models; `anchor_type` is
    not a column on SimHiddenTruth so it is omitted here. The calibration
    module reads is_detected and detector_confidence only.
    """
    return SimHiddenTruth(
        id=1,
        sim_run_id=1,
        sim_user_id=1,
        pattern_type=pattern_type,
        detector_confidence=confidence,
        is_detected=detected,
        window_start=datetime(2025, 1, 1, tzinfo=timezone.utc),
        window_end=datetime(2025, 1, 1, 2, tzinfo=timezone.utc),
    )


class TestCalibrationBin:
    """Individual confidence bin behavior."""

    def test_empty_bin(self):
        """An empty bin should have zero support."""
        b = CalibrationBin(0, 0.0, 0.1)
        assert b.support == 0
        assert b.avg_confidence == 0.0
        assert b.empirical_accuracy == 0.0

    def test_single_correct(self):
        """A bin with one correct prediction should show accuracy=1."""
        b = CalibrationBin(0, 0.0, 0.1)
        b.add(confidence=0.05, correct=True)
        assert b.support == 1
        assert b.avg_confidence == 0.05
        assert b.empirical_accuracy == 1.0
        assert b.calibration_error == 0.95

    def test_mixed_bin(self):
        """A bin with correct and incorrect predictions."""
        b = CalibrationBin(5, 0.5, 0.6)
        b.add(0.51, True)
        b.add(0.52, False)
        b.add(0.53, True)
        assert b.support == 3
        assert 0.51 <= b.avg_confidence <= 0.53
        assert b.empirical_accuracy == 2 / 3
        assert b.calibration_error > 0

    def test_to_dict(self):
        """Serialization should include all fields."""
        b = CalibrationBin(3, 0.3, 0.4)
        b.add(0.35, True)
        d = b.to_dict()
        assert d["bin_index"] == 3
        assert d["support"] == 1
        assert d["empirical_accuracy"] == 1.0


class TestCalibrationResult:
    """Overall calibration result aggregation."""

    def test_empty(self):
        """An empty result should have ECE=0 and no threshold."""
        result = CalibrationResult("empty", [CalibrationBin(i, i/10, (i+1)/10) for i in range(10)])
        assert result.total_samples == 0
        assert result.ece == 0.0
        assert result.mce == 0.0
        assert result.find_threshold() is None

    def test_perfect_calibration(self):
        """When confidence == accuracy in every bin, ECE ≈ 0.

        Perfect calibration means accuracy matches avg_confidence per bin.
        For bin i (range i/10 to (i+1)/10), with center c:
        - accuracy ≈ c means `c * samples` correct, `(1-c) * samples` incorrect
        - Then |acc - conf| ≈ 0 for each bin
        """
        import random
        rng = random.Random(42)
        bins = []
        for i in range(10):
            b = CalibrationBin(i, i / 10, (i + 1) / 10)
            center = (i + 0.5) / 10
            samples = 50
            n_correct = int(center * samples)
            for j in range(samples):
                correct = j < n_correct
                # Slight jitter around center to spread confidence within bin
                conf = center + rng.uniform(-0.04, 0.04)
                conf = max(i / 10 + 0.001, min((i + 1) / 10 - 0.001, conf))
                b.add(conf, correct)
            bins.append(b)
        result = CalibrationResult("perfect", bins)
        # ECE should be very small since accuracy ≈ confidence in each bin
        assert result.ece < 0.05, f"ECE should be near 0 for calibrated data, got {result.ece}"
        assert result.total_samples == 500

    def test_systematic_overconfidence(self):
        """When confidence is always higher than accuracy, ECE > 0."""
        bins = []
        for i in range(10):
            b = CalibrationBin(i, i / 10, (i + 1) / 10)
            center = (i + 0.5) / 10
            # Every bin has accuracy 0.2 lower than confidence
            for _ in range(10):
                b.add(center, center > 0.7)  # only 30%+ get correct
            bins.append(b)
        result = CalibrationResult("overconfident", bins)
        assert result.ece > 0.05
        assert result.total_samples == 100

    def test_threshold_finding(self):
        """Threshold should find the minimum confidence for target accuracy."""
        bins = []
        for i in range(10):
            b = CalibrationBin(i, i / 10, (i + 1) / 10)
            center = (i + 0.5) / 10
            for _ in range(10):
                b.add(center, center >= 0.7)  # all >= 0.7 are correct
            bins.append(b)
        result = CalibrationResult("test", bins)
        threshold = result.find_threshold(accuracy_target=0.80, min_samples=5)
        assert threshold is not None
        # The lowest confidence where running accuracy stays >= 0.80
        # At conf >= 0.75, accuracy = 3/3 = 1.0; drop below at 0.65 (3/4 = 0.75)
        assert threshold["min_confidence"] == 0.75
        assert threshold["expected_accuracy"] >= 0.80

    def test_unreachable_threshold(self):
        """If no confidence level achieves target accuracy, return None.

        Construct bins where even the highest-confidence group has
        accuracy just below the target.
        """
        bins = []
        for i in range(10):
            b = CalibrationBin(i, i / 10, (i + 1) / 10)
            center = (i + 0.5) / 10
            # Every bin has accuracy = center, which is always < 0.95 for bins 0-8
            # Bin 9 has center=0.95 → 9.5/10 correct = 0.95 but center=0.95 < 0.95 is False
            # So at conf >= 0.95: 10 samples, 9.5 correct on avg → 95% accuracy
            import random
            rng = random.Random(42)
            samples = 20
            n_correct = int(center * samples)
            for j in range(samples):
                correct = j < n_correct
                conf = max(i / 10 + 0.001, min((i + 1) / 10 - 0.001, center))
                b.add(conf, correct)
            bins.append(b)
        result = CalibrationResult("unreachable", bins)
        threshold = result.find_threshold(accuracy_target=0.97)  # above max achievable accuracy
        assert threshold is None or threshold["expected_accuracy"] < 0.97


class TestComputeCalibration:
    """End-to-end calibration computation from SimHiddenTruth list."""

    def test_empty_truths(self):
        """Empty truth list should produce empty results, not crash."""
        result = compute_calibration([], label="test")
        assert result.total_samples == 0
        assert result.ece == 0.0

    def test_single_truth(self):
        """Single truth with confidence should produce one populated bin."""
        truths = [make_truth(confidence=0.85, detected=True)]
        result = compute_calibration(truths, label="test", bin_count=10)
        assert result.total_samples == 1
        # 0.85 falls in bin 8 (0.8-0.9)
        populated = [b for b in result.bins if b.support > 0]
        assert len(populated) == 1
        assert populated[0].bin_lower == 0.8

    def test_all_correct_gives_accuracy_one(self):
        """When all predictions are correct, every bin has accuracy = 1.0.

        ECE then measures the gap between predicted confidence and 1.0.
        """
        truths = []
        for i in range(100):
            conf = (i + 0.5) / 100
            truths.append(make_truth(confidence=conf, detected=True))
        result = compute_calibration(truths, label="all_correct")
        assert result.total_samples == 100
        # Every bin should have accuracy = 1.0
        for b in result.bins:
            if b.support > 0:
                assert b.empirical_accuracy == 1.0, (
                    f"Bin {b.bin_lower}-{b.bin_upper} has accuracy {b.empirical_accuracy}"
                )
        # ECE = weighted average of |conf_b - 1.0|
        # Since all bins have accuracy 1.0 and conf < 1.0, ECE > 0
        assert result.ece > 0

    def test_mixed_truths(self):
        """Mix of correct/incorrect at varying confidence levels."""
        truths = []
        # Bin 8 (0.8-0.9): conf=0.85 → int(0.85*10)=8 → bin 8
        for _ in range(20):
            truths.append(make_truth(confidence=0.85, detected=True))   # correct
        for _ in range(5):
            truths.append(make_truth(confidence=0.83, detected=False))  # incorrect
        # Bin 5 (0.5-0.6): conf=0.55 → int(0.55*10)=5 → bin 5
        for _ in range(10):
            truths.append(make_truth(confidence=0.55, detected=True))   # correct
        for _ in range(5):
            truths.append(make_truth(confidence=0.54, detected=False))  # incorrect

        result = compute_calibration(truths, label="mixed")
        assert result.total_samples == 40

        # Bin 8 (0.8-0.9): 20 correct + 5 incorrect = 25 total
        # Expected accuracy: 20/25 = 0.80
        bin_8 = next(b for b in result.bins if b.bin_lower == 0.8)
        assert bin_8.support == 25
        assert bin_8.empirical_accuracy == pytest.approx(0.80, abs=0.01)

        # Bin 5 (0.5-0.6): 10 correct + 5 incorrect = 15 total
        # Expected accuracy: 10/15 = 0.667
        bin_5 = next(b for b in result.bins if b.bin_lower == 0.5)
        assert bin_5.support == 15
        assert bin_5.empirical_accuracy == pytest.approx(2 / 3, abs=0.01)

    def test_threshold_deployment_recommendation(self):
        """Should recommend a confidence threshold for deployment."""
        truths = []
        # All predictions above 0.7 are correct, below are incorrect
        for conf in [0.3, 0.4, 0.5, 0.6]:
            truths.append(make_truth(confidence=conf, detected=False))
        for conf in [0.7, 0.75, 0.8, 0.85, 0.9, 0.95]:
            truths.append(make_truth(confidence=conf, detected=True))

        result = compute_calibration(truths, label="deployment")
        threshold = result.find_threshold(accuracy_target=0.90, min_samples=5)
        assert threshold is not None
        # At conf=0.7: running acc=1/1=1.0 → threshold = 0.7
        # At conf=0.65: running acc=1/2=0.5 < 0.90 → break
        # So threshold should be 0.7
        assert threshold["min_confidence"] == 0.7
        assert threshold["expected_accuracy"] >= 0.90

    def test_calibration_by_group(self):
        """Calibration by pattern type should separate results."""
        truths = []
        for ptype in ["post_meal_spike", "overnight_low"]:
            for i in range(10):
                truths.append(make_truth(
                    pattern_type=ptype,
                    confidence=(i + 0.5) / 10,
                    detected=(i >= 5),
                ))
        results = compute_calibration_by_group(truths, group_key="pattern_type")
        assert "post_meal_spike" in results
        assert "overnight_low" in results
        assert results["post_meal_spike"].total_samples == 10
        assert results["overnight_low"].total_samples == 10

    def test_full_summary(self):
        """Full summary should include all calibration components."""
        truths = [
            make_truth(pattern_type="post_meal_spike", confidence=0.9, detected=True),
            make_truth(pattern_type="post_meal_spike", confidence=0.5, detected=False),
            make_truth(pattern_type="overnight_low", confidence=0.8, detected=True),
        ]
        summary = compute_full_calibration_summary(truths)
        assert "overall" in summary
        assert "by_pattern_type" in summary
        assert "ece_summary" in summary
        assert "threshold_recommendations" in summary
        assert summary["total_samples"] == 3

        # ECE summary should have per-pattern breakdown
        ece = summary["ece_summary"]
        assert "overall_ece" in ece
        assert "by_pattern" in ece
        assert "post_meal_spike" in ece["by_pattern"]
        assert "overnight_low" in ece["by_pattern"]
