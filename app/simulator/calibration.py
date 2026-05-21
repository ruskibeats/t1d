"""Confidence calibration analysis for pattern detector outputs.

Takes the (predicted_confidence, is_correct) pairs produced by the evaluator
and computes:
- Binned calibration curves (empirical accuracy vs predicted confidence)
- Expected Calibration Error (ECE) per detector and per pattern type
- Threshold recommendations for deploying edges in user-facing insights

All inputs flow from the evaluator's truth-to-edge matching step.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from statistics import mean
from typing import Any, Optional

from app.simulator.models import SimHiddenTruth

logger = logging.getLogger(__name__)

# Number of equally-spaced confidence bins
DEFAULT_BIN_COUNT = 10
# Minimum samples per populated bin for a reliable ECE estimate.
# Bins with fewer samples than this are flagged as sparse and merged
# into the nearest neighbor during ECE computation. The raw bins are
# still returned in to_dict() for transparency.
MIN_SAMPLES_PER_BIN = 5
# Minimum number of edge samples required to issue a threshold
# recommendation. Below this count the recommendation is mathematically
# correct but operationally unreliable.
MIN_THRESHOLD_SAMPLES = 10
# Minimum confidence threshold for high-confidence deployment
DEPLOYMENT_ACCURACY_TARGET = 0.80


# TODO(v2): Replace ad-hoc confidence scoring with a learned scoring
# model. Once 240 users × 90 days of truth-labeled edges exist, train
# a logistic regression on features like [delta_peak, time_to_peak_min,
# auc_above, baseline_variance] to predict is_correct. This produces
# naturally calibrated probabilities without needing post-hoc Platt
# scaling or isotonic regression. The current ad-hoc scores
# (0.5 + rise_component*0.3 + peak_component*0.2) are heuristic and
# will show systematic miscalibration in the ECE output.


class CalibrationBin:
    """A single confidence bin from a calibration analysis."""

    def __init__(
        self,
        bin_index: int,
        bin_lower: float,
        bin_upper: float,
    ):
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
        """Absolute difference between avg confidence and empirical accuracy."""
        return abs(self.avg_confidence - self.empirical_accuracy)

    def to_dict(self) -> dict[str, Any]:
        return {
            "bin_index": self.bin_index,
            "bin_lower": round(self.bin_lower, 2),
            "bin_upper": round(self.bin_upper, 2),
            "support": self.support,
            "avg_confidence": round(self.avg_confidence, 4),
            "empirical_accuracy": round(self.empirical_accuracy, 4),
            "calibration_error": round(self.calibration_error, 4),
        }


class CalibrationResult:
    """Calibration analysis for a single detector or pattern type."""

    def __init__(
        self,
        label: str,
        bins: list[CalibrationBin],
    ):
        self.label = label
        self.raw_bins = list(bins)  # keep originals for transparency
        self.bins = self._merge_sparse_bins([b for b in bins if b.support > 0])
        self.merged_bin_indices: list[int] = [
            b.bin_index for b in bins
            if b.support > 0 and b.support < MIN_SAMPLES_PER_BIN
        ]

    def _merge_sparse_bins(self, populated: list[CalibrationBin]) -> list[CalibrationBin]:
        """Merge bins with fewer than MIN_SAMPLES_PER_BIN into nearest neighbor.

        If a bin has too few samples, its data is folded into the nearest
        non-sparse adjacent bin to avoid misleading ECE contributions from
        underpopulated buckets.
        """
        if len(populated) <= 1:
            return populated

        # Sort by bin index
        populated.sort(key=lambda b: b.bin_index)

        # Identify sparse bins
        sparse_indices = {b.bin_index for b in populated if b.support < MIN_SAMPLES_PER_BIN}
        if not sparse_indices:
            return populated

        result: list[CalibrationBin] = []
        # We'll reassign samples from sparse bins into the nearest neighbor
        # by building a new bin list and merging
        dense = [b for b in populated if b.bin_index not in sparse_indices]
        if not dense:
            # All bins are sparse — just return them as-is
            return populated

        for b in populated:
            if b.bin_index not in sparse_indices:
                # Already dense — keep it
                continue
            # Find nearest dense neighbor by bin_index
            nearest = min(
                dense,
                key=lambda db: abs(db.bin_index - b.bin_index),
            )
            for conf, correct in zip(b.confidences, b.is_correct):
                nearest.add(conf, correct)
            logger.info(
                f"Merged sparse bin {b.bin_index} ({b.support} samples, "
                f"conf range {b.bin_lower}-{b.bin_upper}) into bin {nearest.bin_index}"
            )

        return dense

    @property
    def total_samples(self) -> int:
        return sum(b.support for b in self.bins)

    @property
    def ece(self) -> float:
        """Expected Calibration Error.

        ECE = sum_b (n_b / N) * |acc_b - conf_b|

        Weighted average of calibration error across bins, where
        weights are the fraction of samples in each bin.
        """
        if self.total_samples == 0:
            return 0.0
        weighted = sum(
            (b.support / self.total_samples) * b.calibration_error
            for b in self.bins
        )
        return weighted

    @property
    def mce(self) -> float:
        """Maximum Calibration Error — worst-case bin."""
        if not self.bins:
            return 0.0
        return max(b.calibration_error for b in self.bins)

    def find_threshold(
        self,
        accuracy_target: float = DEPLOYMENT_ACCURACY_TARGET,
        min_samples: int = MIN_THRESHOLD_SAMPLES,
    ) -> Optional[dict[str, Any]]:
        """Find the minimum confidence threshold achieving a target accuracy.

        For deployment use: finds the lowest confidence t such that
        all edges with confidence >= t have empirical accuracy >= target
        and at least ``min_samples`` edges fall above the threshold.

        Algorithm: scan from high confidence downward, tracking running
        accuracy. The first position where running accuracy drops below
        target defines the stop point; the threshold is the confidence
        of the sample just before the drop.

        Args:
            accuracy_target: Desired empirical accuracy (default 0.80).
            min_samples: Minimum number of samples above threshold
                required for a recommendation (default 10).

        Returns:
            Dict with threshold info, or None if target unreachable
            or sample count too low.
        """
        if self.total_samples < min_samples:
            logger.info(
                f"Skipping threshold for '{self.label}': only "
                f"{self.total_samples} samples (need {min_samples})"
            )
            return None
        if not self.bins:
            return None

        # Sort bins by lower bound descending
        sorted_bins = sorted(self.bins, key=lambda b: b.bin_lower, reverse=True)

        # Build list of (confidence, is_correct) from high to low
        pairs: list[tuple[float, bool]] = []
        for b in sorted_bins:
            for conf, correct in zip(b.confidences, b.is_correct):
                pairs.append((conf, correct))

        if not pairs:
            return None

        # Sort by confidence descending.
        sorted_pairs = sorted(pairs, key=lambda x: x[0], reverse=True)

        # Find the LOWEST unique confidence value t such that the
        # accuracy of all samples with confidence >= t meets target.
        #
        # Algorithm: iterate unique confidence values from low to high.
        # For each candidate threshold t, compute accuracy of all samples
        # with conf >= t. Return the lowest t where accuracy >= target.
        unique_confs = sorted(set(c for c, _ in pairs))

        # For each unique confidence value c, find the LAST position
        # of c in the descending-sorted list. The prefix ending at that
        # position contains all samples with conf >= c.
        conf_to_last_pos: dict[float, int] = {}
        for i, (conf, _) in enumerate(sorted_pairs):
            conf_to_last_pos[conf] = i  # overwrites → last occurrence

        # Build prefix (running) statistics: for position i, how many
        # correct and total samples from 0 to i (inclusive).
        prefix_correct = 0

        # Scan from HIGH to LOW unique confidence values.
        # For each unique conf c, compute accuracy of all samples with
        # conf >= c. The FIRST c (lowest) where accuracy >= target is
        # the most inclusive threshold.
        best_threshold = None
        best_accuracy = 0.0
        best_count = 0

        for conf in reversed(unique_confs):
            last_pos = conf_to_last_pos[conf]
            # Prefix up to last_pos includes all samples with conf >= c
            prefix_len = last_pos + 1

            # Count correct in this prefix (not the most efficient,
            # but pairs is small — at most ~1000)
            group_correct = sum(1 for _, ok in sorted_pairs[:prefix_len] if ok)
            accuracy = group_correct / prefix_len

            if accuracy >= accuracy_target:
                best_threshold = conf
                best_accuracy = accuracy
                best_count = prefix_len
            else:
                break

        if best_threshold is None:
            return None

        if best_count < min_samples:
            logger.info(
                f"Skipping threshold for '{self.label}': only "
                f"{best_count} samples above threshold (need {min_samples})"
            )
            return None

        return {
            "accuracy_target": accuracy_target,
            "min_confidence": round(best_threshold, 3),
            "expected_accuracy": round(best_accuracy, 3),
            "samples_above_threshold": best_count,
            "total_samples": len(pairs),
            "recall_at_threshold": round(best_count / len(pairs), 3),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "total_samples": self.total_samples,
            "ece": round(self.ece, 4),
            "mce": round(self.mce, 4),
            "bins": [b.to_dict() for b in self.bins],
            "raw_bins": [b.to_dict() for b in self.raw_bins if b.support > 0],
            "merged_bin_indices": self.merged_bin_indices,
            "min_samples_per_bin": MIN_SAMPLES_PER_BIN,
            "threshold": self.find_threshold(),
            "high_conf_threshold": self.find_threshold(accuracy_target=0.90),
        }


def compute_calibration(
    truths: list[SimHiddenTruth],
    label: str = "pattern_service",
    bin_count: int = DEFAULT_BIN_COUNT,
) -> CalibrationResult:
    """Compute calibration analysis from matched truth labels.

    Args:
        truths: List of SimHiddenTruth with is_detected and detector_confidence.
        label: Label for the result (detector name or pattern type).
        bin_count: Number of confidence bins.

    Returns:
        CalibrationResult with binned accuracy, ECE, and threshold.
    """
    # Collect (confidence, is_correct) pairs from truths that have both fields
    pairs = [
        (t.detector_confidence, bool(t.is_detected))
        for t in truths
        if t.detector_confidence is not None and t.is_detected is not None
    ]

    if not pairs:
        logger.warning(f"No confidence/correct pairs for '{label}' calibration")
        empty_bins = [
            CalibrationBin(i, i / bin_count, (i + 1) / bin_count)
            for i in range(bin_count)
        ]
        return CalibrationResult(label, empty_bins)

    # Create bins
    bins = [
        CalibrationBin(i, i / bin_count, (i + 1) / bin_count)
        for i in range(bin_count)
    ]

    for confidence, correct in pairs:
        # Clamp to [0, 1)
        confidence = max(0.0, min(0.999, confidence))
        bin_idx = min(int(confidence * bin_count), bin_count - 1)
        bins[bin_idx].add(confidence, correct)

    return CalibrationResult(label, bins)


def compute_calibration_by_group(
    truths: list[SimHiddenTruth],
    group_key: str = "pattern_type",
    bin_count: int = DEFAULT_BIN_COUNT,
) -> dict[str, CalibrationResult]:
    """Compute calibration separately per group (pattern type or anchor type).

    Args:
        truths: List of matched SimHiddenTruth instances.
        group_key: Attribute name to group by ('pattern_type' or 'anchor_type').
        bin_count: Number of confidence bins.

    Returns:
        Dict mapping group value → CalibrationResult.
    """
    groups: dict[str, list[SimHiddenTruth]] = defaultdict(list)
    for t in truths:
        key = getattr(t, group_key, "unknown")
        groups[str(key)].append(t)

    return {
        key: compute_calibration(group, label=key, bin_count=bin_count)
        for key, group in groups.items()
    }


def compute_full_calibration_summary(
    truths: list[SimHiddenTruth],
) -> dict[str, Any]:
    """Compute complete calibration summary for a simulation run.

    Produces per-pattern, per-anchor, and overall calibration metrics,
    plus threshold recommendations.

    Args:
        truths: All SimHiddenTruth instances for a run (post-matching).

    Returns:
        Dict with calibration results for API consumption.
    """
    overall = compute_calibration(truths, label="overall")
    by_pattern = compute_calibration_by_group(truths, group_key="pattern_type")
    by_anchor = compute_calibration_by_group(truths, group_key="anchor_type")

    recommendations: list[dict[str, Any]] = []

    # Overall threshold
    overall_threshold = overall.find_threshold()
    if overall_threshold:
        recommendations.append({
            "detector": "overall",
            **overall_threshold,
        })

    # Per-pattern thresholds
    for ptype, result in by_pattern.items():
        threshold = result.find_threshold()
        if threshold:
            recommendations.append({
                "detector": ptype,
                **threshold,
            })

    return {
        "overall": overall.to_dict(),
        "by_pattern_type": {k: v.to_dict() for k, v in by_pattern.items()},
        "by_anchor_type": {k: v.to_dict() for k, v in by_anchor.items()},
        "ece_summary": {
            "overall_ece": round(overall.ece, 4),
            "by_pattern": {k: round(v.ece, 4) for k, v in by_pattern.items()},
            "by_anchor": {k: round(v.ece, 4) for k, v in by_anchor.items()},
        },
        "threshold_recommendations": recommendations,
        "total_samples": overall.total_samples,
    }
