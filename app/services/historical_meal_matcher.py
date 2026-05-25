"""Historical Meal Matching Service.

Finds meals similar to a given composition in the user's historical data
and computes the average observed glucose impact. This is the core
educational feature: "Last time you ate this, here's what happened."

Data sources (searched in order):
1. food_history_90d.json — 90-day calibrated/curated meal records (3,251 entries)
2. food_entries + glucose_readings DB tables (future: live user data)

Safety: Returns educational observations only, never dosing instructions.
"""

import json
import math
import logging
from statistics import stdev
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Config ──

_FOOD_HISTORY_PATH = Path("/root/t1d/data/food_history_90d.json")

# Default similarity thresholds
_DEFAULT_CARB_TOLERANCE_G = 15      # ±15g carbs for "similar"
_DEFAULT_FAT_TOLERANCE_G = 10       # ±10g fat
_DEFAULT_MAX_MATCHES = 10           # Max similar meals to return
_DEFAULT_MIN_MATCHES = 3            # Min matches needed for a reliable average

# ── Data types ──


@dataclass
class HistoricalMealMatch:
    """A single matched historical meal entry."""
    food_name: str
    timestamp: str
    carb_estimate_g: float
    fat_g: float
    bolus_units: float
    peak_delta_mgdl: Optional[float]
    peak_time_minutes: Optional[float]
    anchor_type: str
    similarity_score: float = 0.0


@dataclass
class HistoricalMealSummary:
    """Aggregated summary of matched historical meals."""
    query_description: str
    query_carbs_g: float
    query_fat_g: float
    matches_found: int
    avg_carbs_g: float
    avg_fat_g: float
    avg_bolus_units: Optional[float]
    avg_peak_delta_mgdl: Optional[float]
    avg_peak_time_minutes: Optional[float]
    min_peak_delta_mgdl: Optional[float]
    max_peak_delta_mgdl: Optional[float]
    confidence_tier: str = "low"
    confidence_score: float = 0.0
    matched_meals: List[HistoricalMealMatch] = field(default_factory=list)
    narrative: str = ""
    disclaimer: str = (
        "This is an educational observation from historical meal data, "
        "not medical advice. Actual glucose impact depends on many factors "
        "including current glucose, insulin-on-board, activity, and stress."
    )


# ── Data loading ──


def _load_food_history() -> List[Dict[str, Any]]:
    """Load food history data from JSON file.

    Returns empty list if file is missing or unreadable.
    """
    if not _FOOD_HISTORY_PATH.exists():
        logger.warning(f"Food history file not found: {_FOOD_HISTORY_PATH}")
        return []
    try:
        with open(_FOOD_HISTORY_PATH) as f:
            data = json.load(f)
        if isinstance(data, list):
            logger.info(f"Loaded {len(data)} food history entries")
            return data
        logger.warning(f"Unexpected food history format: {type(data).__name__}")
        return []
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load food history: {e}")
        return []


def _normalize_meal_query(
    carbs_g: Optional[float] = None,
    fat_g: Optional[float] = None,
    food_name: Optional[str] = None,
) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Normalize and validate meal query parameters."""
    if carbs_g is not None and carbs_g < 0:
        carbs_g = None
    if fat_g is not None and fat_g < 0:
        fat_g = None
    food_name = food_name.strip().lower() if food_name else None
    return carbs_g, fat_g, food_name


def _nutrient_distance(
    entry_carbs: float, entry_fat: float,
    query_carbs: float, query_fat: float,
) -> float:
    """Compute nutrient similarity distance between two meals.

    Lower is more similar. Uses normalized Euclidean distance.
    Returns 0.0 for identical, 1.0+ for very different.
    """
    if entry_carbs <= 0:
        return float("inf")
    carb_diff = abs(entry_carbs - query_carbs) / _DEFAULT_CARB_TOLERANCE_G
    fat_diff = abs(entry_fat - query_fat) / max(_DEFAULT_FAT_TOLERANCE_G, 1)
    return math.sqrt(carb_diff ** 2 + fat_diff ** 2)


def _text_similarity(entry_name: str, query_name: str) -> float:
    """Compute text similarity score (0.0 to 1.0) between two food names.

    Uses token overlap. Higher is more similar.
    """
    if not query_name or not entry_name:
        return 0.0
    entry_tokens = set(entry_name.lower().split())
    query_tokens = set(query_name.lower().split())
    if not entry_tokens or not query_tokens:
        return 0.0
    intersection = entry_tokens & query_tokens
    union = entry_tokens | query_tokens
    return len(intersection) / len(union)


# ── Core matching logic ──


def find_similar_meals(
    carbs_g: Optional[float] = None,
    fat_g: Optional[float] = None,
    food_name: Optional[str] = None,
    max_matches: int = _DEFAULT_MAX_MATCHES,
    min_matches: int = _DEFAULT_MIN_MATCHES,
    carb_tolerance_g: float = _DEFAULT_CARB_TOLERANCE_G,
    fat_tolerance_g: float = _DEFAULT_FAT_TOLERANCE_G,
) -> List[HistoricalMealMatch]:
    """Find meals in historical data similar to the given composition.

    Args:
        carbs_g: Total carbohydrate grams in the query meal.
        fat_g: Total fat grams in the query meal.
        food_name: Optional food name for text-based matching.
        max_matches: Maximum number of similar meals to return.
        min_matches: Minimum matches needed for reliable aggregation.
        carb_tolerance_g: Carb tolerance for nutrient distance.
        fat_tolerance_g: Fat tolerance for nutrient distance.

    Returns:
        List of HistoricalMealMatch sorted by similarity (most similar first).
    """
    history = _load_food_history()
    if not history:
        logger.warning("No food history data available for matching")
        return []

    carbs_g, fat_g, food_name = _normalize_meal_query(carbs_g, fat_g, food_name)
    if carbs_g is None and food_name is None:
        logger.warning("Historical meal matching requires carbs or food name")
        return []

    scored: List[Tuple[float, Dict[str, Any]]] = []

    for entry in history:
        entry_carbs = float(entry.get("carb_estimate_g", 0) or 0)
        entry_fat = float(entry.get("fat_g", 0) or 0)
        entry_name = str(entry.get("food", "") or "")

        # Skip entries without carb data
        if entry_carbs <= 0:
            continue

        # Compute combined distance score
        nutrient_dist = float("inf")
        text_score = 0.0

        if carbs_g is not None:
            nutrient_dist = _nutrient_distance(
                entry_carbs, entry_fat, carbs_g, fat_g or 0
            )

        if food_name:
            text_score = _text_similarity(entry_name, food_name)
            # Text match within carb tolerance is a strong signal
            if text_score > 0.3 and carbs_g is not None and abs(entry_carbs - carbs_g) <= carb_tolerance_g * 2:
                nutrient_dist = min(nutrient_dist, 1.0)

        # Skip if outside basic carb tolerance and no text match
        if carbs_g is not None and nutrient_dist > 2.0 and text_score < 0.5:
            continue
        if carbs_g is None and text_score < 0.3:
            continue

        # Combined score (lower = better match)
        combined_score = nutrient_dist - text_score
        scored.append((combined_score, entry))

    # Sort by score (ascending = best match)
    scored.sort(key=lambda x: x[0])

    # Build results
    results = []
    for score, entry in scored[:max_matches]:
        cgm = entry.get("cgm_impact", {}) or {}
        results.append(HistoricalMealMatch(
            food_name=str(entry.get("food", "")),
            timestamp=str(entry.get("timestamp", "")),
            carb_estimate_g=float(entry.get("carb_estimate_g", 0)),
            fat_g=float(entry.get("fat_g", 0)),
            bolus_units=float(entry.get("bolus_units", 0)),
            peak_delta_mgdl=cgm.get("expected_peak_delta"),
            peak_time_minutes=cgm.get("peak_time_minutes"),
            anchor_type=str(entry.get("anchor_type", "")),
            similarity_score=round(1.0 / (1.0 + score), 3),
        ))

    return results


def summarize_similar_meals(
    query_description: str,
    carbs_g: Optional[float] = None,
    fat_g: Optional[float] = None,
    food_name: Optional[str] = None,
) -> HistoricalMealSummary:
    """Find and summarize similar historical meals for educational output.

    This is the main public API. It finds similar meals, computes averages,
    and returns a structured summary with educational narrative.

    Args:
        query_description: Human-readable description of the query meal.
        carbs_g: Total carbohydrate grams in the query meal.
        fat_g: Total fat grams in the query meal.
        food_name: Optional food name for text matching.

    Returns:
        HistoricalMealSummary with averages, ranges, and educational narrative.
    """
    matches = find_similar_meals(
        carbs_g=carbs_g,
        fat_g=fat_g,
        food_name=food_name,
    )

    if not matches:
        return HistoricalMealSummary(
            query_description=query_description,
            query_carbs_g=carbs_g or 0,
            query_fat_g=fat_g or 0,
            matches_found=0,
            avg_carbs_g=carbs_g or 0,
            avg_fat_g=fat_g or 0,
            avg_bolus_units=None,
            avg_peak_delta_mgdl=None,
            avg_peak_time_minutes=None,
            min_peak_delta_mgdl=None,
            max_peak_delta_mgdl=None,
            narrative=(
                "No similar meals found in historical data. "
                "Monitor your response and log this meal for future comparisons."
            ),
        )

    # Compute averages
    match_count = len(matches)
    avg_carbs = sum(m.carb_estimate_g for m in matches) / match_count
    avg_fat = sum(m.fat_g for m in matches) / match_count
    avg_bolus = sum(m.bolus_units for m in matches) / match_count

    peak_deltas = [m.peak_delta_mgdl for m in matches if m.peak_delta_mgdl is not None]
    peak_times = [m.peak_time_minutes for m in matches if m.peak_time_minutes is not None]

    avg_peak_delta = sum(peak_deltas) / len(peak_deltas) if peak_deltas else None
    avg_peak_time = sum(peak_times) / len(peak_times) if peak_times else None
    min_peak = min(peak_deltas) if peak_deltas else None
    max_peak = max(peak_deltas) if peak_deltas else None

    # Build educational narrative (safety: observations only, no dosing directives)
    narrative_parts = [f"Found {match_count} similar meals in your history."]

    if avg_peak_delta is not None:
        narrative_parts.append(
            f"Similar meals had an average glucose rise of ~{avg_peak_delta:.0f} mg/dL, "
            f"ranging from {min_peak:.0f} to {max_peak:.0f} mg/dL."
        )

    if avg_peak_time is not None:
        narrative_parts.append(
            f"The glucose peak typically occurred around {avg_peak_time:.0f} minutes after eating."
        )

    if avg_bolus is not None:
        narrative_parts.append(
            f"On average, similar meals used {avg_bolus:.1f} units with a 1:"
            f"{round(avg_carbs / avg_bolus, 1) if avg_bolus > 0 else '?'} ratio."
        )

    # Add fat-driven notes
    if avg_fat >= 15:
        narrative_parts.append(
            "Several matched meals were higher in fat, which can delay "
            "the glucose peak by 1-2 hours beyond the typical window."
        )

    narrative = " ".join(narrative_parts)

    # Compute confidence scoring
    from app.services.confidence_scoring_service import score_and_narrate

    peak_deltas_clean = [d for d in peak_deltas if d is not None]
    peak_delta_cv = None
    if len(peak_deltas_clean) >= 3:
        try:
            mean_pd = sum(peak_deltas_clean) / len(peak_deltas_clean)
            if mean_pd > 0:
                sd = stdev(peak_deltas_clean)
                peak_delta_cv = sd / mean_pd
        except Exception:
            pass

    confidence = score_and_narrate(
        match_count=match_count,
        avg_similarity=sum(m.similarity_score for m in matches) / match_count if match_count > 0 else 0,
        has_cgm_data=bool(peak_deltas),
    )

    return HistoricalMealSummary(
        query_description=query_description,
        query_carbs_g=carbs_g or 0,
        query_fat_g=fat_g or 0,
        matches_found=match_count,
        avg_carbs_g=round(avg_carbs, 1),
        avg_fat_g=round(avg_fat, 1),
        avg_bolus_units=round(avg_bolus, 1) if avg_bolus else None,
        avg_peak_delta_mgdl=round(avg_peak_delta, 0) if avg_peak_delta else None,
        avg_peak_time_minutes=round(avg_peak_time, 0) if avg_peak_time else None,
        min_peak_delta_mgdl=round(min_peak, 0) if min_peak else None,
        max_peak_delta_mgdl=round(max_peak, 0) if max_peak else None,
        matched_meals=matches[:5],
        narrative=narrative,
        confidence_tier=confidence.tier,
        confidence_score=confidence.overall_score,
    )


# ── Convenience for the companion loop ──


def historical_context_for_meal(
    food_name: str,
    estimated_carbs_g: float,
    estimated_fat_g: float,
) -> Dict[str, Any]:
    """Generate historical context for a meal, suitable for companion pipeline.

    Returns a dict compatible with the companion's context format.
    """
    summary = summarize_similar_meals(
        query_description=food_name,
        carbs_g=estimated_carbs_g,
        fat_g=estimated_fat_g,
        food_name=food_name,
    )
    return {
        "has_history": summary.matches_found > 0,
        "matches_found": summary.matches_found,
        "avg_carbs_g": summary.avg_carbs_g,
        "avg_fat_g": summary.avg_fat_g,
        "avg_bolus_units": summary.avg_bolus_units,
        "avg_peak_delta_mgdl": summary.avg_peak_delta_mgdl,
        "avg_peak_time_minutes": summary.avg_peak_time_minutes,
        "narrative": summary.narrative,
        "confidence_tier": summary.confidence_tier,
        "confidence_score": summary.confidence_score,
        "disclaimer": summary.disclaimer,
    }