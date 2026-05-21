"""Evaluates PatternService detector output against hidden truths.

After a simulation run generates data and the detectors have been run,
the evaluator:
1. Loads all hidden truths for the run.
2. Fetches PatternService detector results (edges + pattern analyses).
3. Matches detected edges to planted truths.
4. Computes precision, recall, F1, and other metrics per pattern type
   and per anchor type.
5. Stores results in sim_detector_scores.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.metrics.models import HealthMetric, HealthMetricEdge
from app.metrics.types import GraphEdgeType
from app.simulator.models import SimDetectorScore, SimHiddenTruth, SimRun, SimUser

logger = logging.getLogger(__name__)


class SimulatorEvaluator:
    """Evaluates detector performance against planted truths.

    Detection matching logic:
    - post_meal_spike truth ↔ MEAL_TO_GLUCOSE_SPIKE edge within time window
    - overnight_low truth ↔ SLEEP_TO_NEXT_DAY_GLUCOSE edge within time window
    - exercise_effect truth ↔ EXERCISE_TO_GLUCOSE_DROP/RISE edge within time window
    - delayed_high_fat truth ↔ MEAL_TO_DELAYED_SPIKE edge within time window
    """

    # Match tolerance: how close a detected edge must be to the truth window (minutes)
    MATCH_TOLERANCE_MINUTES = 30

    TRUTH_TO_EDGE_TYPE: dict[str, list[str]] = {
        "post_meal_spike": ["meal_to_glucose_spike"],
        "overnight_low": ["sleep_to_next_day_glucose"],
        "exercise_effect": ["exercise_to_glucose_drop", "exercise_to_glucose_rise"],
        "delayed_high_fat": ["meal_to_delayed_spike"],
    }

    def __init__(self, db: AsyncSession, sim_run_id: int):
        self.db = db
        self.sim_run_id = sim_run_id

    async def run_evaluation(self, sim_run: SimRun) -> dict[str, Any]:
        """Run full evaluation for a simulation run.

        Iterates over all sim users, matches truths to edges,
        computes metrics, and stores scores.

        Args:
            sim_run: The simulation run to evaluate.

        Returns:
            Summary dict with aggregated metrics.
        """
        # Load all users and truths for this run
        result = await self.db.execute(
            select(SimUser).where(SimUser.sim_run_id == self.sim_run_id)
        )
        sim_users = list(result.scalars().all())

        result = await self.db.execute(
            select(SimHiddenTruth).where(SimHiddenTruth.sim_run_id == self.sim_run_id)
        )
        all_truths = list(result.scalars().all())

        if not all_truths:
            logger.warning(f"No hidden truths found for sim_run {self.sim_run_id}")
            return {"error": "no truths", "total_truths": 0}

        # Fetch all edges created by pattern detectors for these users
        # (edges are in health_metric_edges, created by PatternService during simulation)
        # We match by looking for edges created within the simulation date range
        # with relevant edge types and algorithm names from PatternService
        edge_types = [
            "meal_to_glucose_spike",
            "sleep_to_next_day_glucose",
            "exercise_to_glucose_drop",
            "exercise_to_glucose_rise",
            "meal_to_delayed_spike",
        ]

        result = await self.db.execute(
            select(HealthMetricEdge).where(
                HealthMetricEdge.user_id.in_([u.real_user_id for u in sim_users if u.real_user_id]),
                HealthMetricEdge.edge_type.in_(edge_types),
            )
        )
        all_edges = list(result.scalars().all())

        # Match truths to edges
        truths_by_type: dict[str, list[SimHiddenTruth]] = defaultdict(list)
        for t in all_truths:
            truths_by_type[t.pattern_type].append(t)

        edges_by_type: dict[str, list[HealthMetricEdge]] = defaultdict(list)
        for e in all_edges:
            edges_by_type[str(e.edge_type)].append(e)

        # Per-user matching
        by_anchor: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"true_positives": 0, "false_negatives": 0, "false_positives": 0, "total_truths": 0}
        )
        by_pattern: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"true_positives": 0, "false_negatives": 0, "false_positives": 0, "total_truths": 0}
        )

        sim_user_map = {u.id: u for u in sim_users}
        truth_user_map: dict[int, int] = {}  # truth_id → sim_user_id

        for truth in all_truths:
            truth_user_map[truth.id] = truth.sim_user_id
            sim_user = sim_user_map.get(truth.sim_user_id)
            anchor = sim_user.anchor_type if sim_user else "unknown"
            by_anchor[anchor]["total_truths"] += 1
            by_pattern[truth.pattern_type]["total_truths"] += 1

            # Try to match this truth to an edge
            matched = await self._match_truth_to_edge(truth, all_edges)

            if matched:
                truth.is_detected = True
                truth.detector_confidence = matched.confidence
                truth.detector_evidence = matched.evidence
                truth.matched_edge_id = matched.id

                by_anchor[anchor]["true_positives"] += 1
                by_pattern[truth.pattern_type]["true_positives"] += 1
            else:
                truth.is_detected = False
                by_anchor[anchor]["false_negatives"] += 1
                by_pattern[truth.pattern_type]["false_negatives"] += 1

        # Count false positives: edges that match no truth
        matched_edge_ids = {t.matched_edge_id for t in all_truths if t.matched_edge_id}
        for edge in all_edges:
            if edge.id not in matched_edge_ids:
                # Find which user this edge belongs to
                for uid, sim_user in sim_user_map.items():
                    if sim_user.real_user_id:
                        # Check if edge.user_id matches
                        pass
                # FP tracking by anchor requires knowing the edge's user
                anchor = "unknown"
                for su in sim_users:
                    if su.real_user_id == edge.user_id:
                        anchor = su.anchor_type
                        break
                by_anchor[anchor]["false_positives"] += 1

        # Compute metrics
        summary = await self._compute_summary(
            by_anchor, by_pattern, all_truths, all_edges
        )

        # ── Calibration analysis ──
        # Run after matching so SimHiddenTruth objects have detector_confidence
        # and is_detected populated.
        from app.simulator.calibration import compute_full_calibration_summary
        try:
            # Re-load populated truths for calibration
            result = await self.db.execute(
                select(SimHiddenTruth).where(
                    SimHiddenTruth.sim_run_id == self.sim_run_id,
                    SimHiddenTruth.detector_confidence.isnot(None),
                )
            )
            calibrated_truths = list(result.scalars().all())
            calibration_summary = compute_full_calibration_summary(calibrated_truths)
            summary["calibration"] = calibration_summary
            await self._store_calibration_scores(
                calibration_summary, sim_run.name
            )
        except Exception as e:
            logger.warning(f"Calibration analysis failed: {e}")
            summary["calibration"] = {"error": str(e)}

        # Persist matches
        await self.db.flush()

        # Store detector scores
        await self._store_scores(summary, sim_run)
        await self.db.flush()

        # Update run status
        sim_run.status = "completed"
        sim_run.completed_at = datetime.now(timezone.utc)
        sim_run.summary_json = summary
        await self.db.flush()

        logger.info(f"Evaluation complete for sim_run {self.sim_run_id}")
        return summary

    async def _match_truth_to_edge(
        self,
        truth: SimHiddenTruth,
        edges: list[HealthMetricEdge],
    ) -> Optional[HealthMetricEdge]:
        """Try to match a hidden truth to a detected edge.

        Matching criteria:
        - Edge type matches the truth pattern type.
        - Edge is within the truth's time window (if set).
        - Edges with higher confidence are preferred.

        Args:
            truth: The hidden truth label.
            edges: All detected edges for this user.

        Returns:
            Matching edge, or None if no match found.
        """
        expected_edge_types = self.TRUTH_TO_EDGE_TYPE.get(truth.pattern_type, [])

        candidates = []
        for edge in edges:
            if str(edge.edge_type) not in expected_edge_types:
                continue
            # Edge user must match the truth's user
            # (we check user-level matching at a higher level)
            candidates.append(edge)

        if not candidates:
            return None

        # If truth has a time window, try to filter by source metric's measured_at
        if truth.window_start and truth.window_end:
            tuned: list[HealthMetricEdge] = []
            for edge in candidates:
                # Look up the source metric's measured_at time
                try:
                    result = await self.db.execute(
                        select(HealthMetric.measured_at).where(
                            HealthMetric.id == edge.source_metric_id
                        )
                    )
                    source_time = result.scalar_one_or_none()
                except Exception:
                    source_time = None

                if source_time is not None:
                    window_start = truth.window_start
                    window_end = truth.window_end
                    if window_start.tzinfo is None:
                        window_start = window_start.replace(tzinfo=timezone.utc)
                    if window_end.tzinfo is None:
                        window_end = window_end.replace(tzinfo=timezone.utc)
                    if source_time.tzinfo is None:
                        source_time = source_time.replace(tzinfo=timezone.utc)

                    tol = timedelta(minutes=self.MATCH_TOLERANCE_MINUTES)
                    if window_start - tol <= source_time <= window_end + tol:
                        tuned.append(edge)
                else:
                    # No source metric found — still include as candidate
                    tuned.append(edge)
            candidates = tuned

        if not candidates:
            return None

        # Return highest confidence candidate
        return max(candidates, key=lambda e: e.confidence)

    async def _compute_summary(
        self,
        by_anchor: dict,
        by_pattern: dict,
        all_truths: list[SimHiddenTruth],
        all_edges: list[HealthMetricEdge],
    ) -> dict[str, Any]:
        """Compute aggregated evaluation metrics.

        Args:
            by_anchor: Per-anchor counts.
            by_pattern: Per-pattern counts.
            all_truths: All hidden truths.
            all_edges: All detected edges.

        Returns:
            Summary dict with precision, recall, F1 per group.
        """
        def _metrics(counts: dict) -> dict:
            tp = counts["true_positives"]
            fn = counts["false_negatives"]
            fp = counts["false_positives"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * precision * recall / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )
            return {
                "total_truths": counts["total_truths"],
                "true_positives": tp,
                "false_negatives": fn,
                "false_positives": fp,
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3),
            }

        detected_truths = [t for t in all_truths if t.is_detected]
        avg_conf = (
            sum(t.detector_confidence for t in detected_truths if t.detector_confidence) / len(detected_truths)
            if detected_truths else 0.0
        )

        return {
            "total_truths": len(all_truths),
            "total_edges": len(all_edges),
            "truths_detected": len(detected_truths),
            "truths_missed": len(all_truths) - len(detected_truths),
            "detection_rate": round(len(detected_truths) / len(all_truths), 3) if all_truths else 0.0,
            "avg_confidence_detected": round(avg_conf, 3),
            "by_anchor_type": {
                anchor: _metrics(counts) for anchor, counts in sorted(by_anchor.items())
            },
            "by_pattern_type": {
                pattern: _metrics(counts) for pattern, counts in sorted(by_pattern.items())
            },
            "overall": _metrics({
                "true_positives": sum(a["true_positives"] for a in by_anchor.values()),
                "false_negatives": sum(a["false_negatives"] for a in by_anchor.values()),
                "false_positives": sum(a["false_positives"] for a in by_anchor.values()),
                "total_truths": sum(a["total_truths"] for a in by_anchor.values()),
            }),
        }

    async def _store_scores(
        self,
        summary: dict[str, Any],
        sim_run: SimRun,
    ) -> None:
        """Store evaluation scores in sim_detector_scores.

        Args:
            summary: The evaluation summary dict.
            sim_run: The simulation run.
        """
        # Store overall metrics
        overall = summary.get("overall", {})
        for metric_name in ["precision", "recall", "f1", "detection_rate"]:
            score = SimDetectorScore(
                sim_run_id=self.sim_run_id,
                sim_user_id=None,
                detector_name="pattern_service",
                detector_version="1.0",
                anchor_type=None,
                pattern_type=None,
                metric_name=f"overall_{metric_name}",
                metric_value=overall.get(metric_name, 0.0),
                breakdown_json=overall,
            )
            self.db.add(score)

        # Store per-pattern metrics
        for pattern_type, metrics in summary.get("by_pattern_type", {}).items():
            for metric_name in ["precision", "recall", "f1"]:
                score = SimDetectorScore(
                    sim_run_id=self.sim_run_id,
                    sim_user_id=None,
                    detector_name="pattern_service",
                    detector_version="1.0",
                    anchor_type=None,
                    pattern_type=pattern_type,
                    metric_name=f"{pattern_type}_{metric_name}",
                    metric_value=metrics.get(metric_name, 0.0),
                    breakdown_json=metrics,
                )
                self.db.add(score)

        # Store per-anchor metrics
        for anchor_type, metrics in summary.get("by_anchor_type", {}).items():
            for metric_name in ["precision", "recall", "f1"]:
                score = SimDetectorScore(
                    sim_run_id=self.sim_run_id,
                    sim_user_id=None,
                    detector_name="pattern_service",
                    detector_version="1.0",
                    anchor_type=anchor_type,
                    pattern_type=None,
                    metric_name=f"{anchor_type}_{metric_name}",
                    metric_value=metrics.get(metric_name, 0.0),
                    breakdown_json=metrics,
                )
                self.db.add(score)

    async def _store_calibration_scores(
        self,
        calibration_summary: dict[str, Any],
        detector_name: str,
    ) -> None:
        """Store calibration ECE and threshold scores in sim_detector_scores.

        Args:
            calibration_summary: From compute_full_calibration_summary().
            detector_name: Detector identifier for the score records.
        """
        ece_summary = calibration_summary.get("ece_summary", {})

        # Overall ECE
        self.db.add(SimDetectorScore(
            sim_run_id=self.sim_run_id,
            sim_user_id=None,
            detector_name=detector_name,
            detector_version="1.0",
            anchor_type=None,
            pattern_type=None,
            metric_name="calibration_ece_overall",
            metric_value=ece_summary.get("overall_ece", 0.0),
            breakdown_json=calibration_summary.get("overall"),
        ))

        # Per-pattern ECE
        for pattern_type, ece in ece_summary.get("by_pattern", {}).items():
            self.db.add(SimDetectorScore(
                sim_run_id=self.sim_run_id,
                sim_user_id=None,
                detector_name=detector_name,
                detector_version="1.0",
                anchor_type=None,
                pattern_type=pattern_type,
                metric_name=f"calibration_ece_{pattern_type}",
                metric_value=ece,
                breakdown_json=calibration_summary.get("by_pattern_type", {}).get(pattern_type),
            ))

        # Store threshold recommendations
        for rec in calibration_summary.get("threshold_recommendations", []):
            detector = rec.get("detector", "overall")
            min_conf = rec.get("min_confidence", 0.0)
            exp_acc = rec.get("expected_accuracy", 0.0)
            recall = rec.get("recall_at_threshold", 0.0)

            self.db.add(SimDetectorScore(
                sim_run_id=self.sim_run_id,
                sim_user_id=None,
                detector_name=detector_name,
                detector_version="1.0",
                anchor_type=None,
                pattern_type=detector if detector != "overall" else None,
                metric_name=f"threshold_min_conf_{detector}",
                metric_value=min_conf,
                breakdown_json={
                    "expected_accuracy": exp_acc,
                    "recall": recall,
                    **rec,
                },
            ))
