"""Confidence Scoring Service — data quality metrics for the companion pipeline.

Synthesizes confidence across multiple dimensions to answer:
"How reliable is this information I'm showing the user?"

The service combines:
1. Food data provenance (barcode match, trust tier, quality flags)
2. Historical match quality (sample size, similarity, consistency)
3. Data completeness (nutrient fields available)
4. Source trust (official vs community vs estimated)

Produces a single confidence score (0.0-1.0), a tier label, decomposed
component scores, and an educational narrative.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ── Tiers ──

CONFIDENCE_TIERS: list[tuple[float, str, str]] = [
    (0.8, "high", "This information is based on reliable, well-matched data."),
    (0.5, "moderate", "This information is based on reasonable data, but individual results may vary."),
    (0.0, "low", "Limited data is available. Monitor your response and log this for future comparisons."),
]


# ── Input types ──


@dataclass
class FoodProvenanceInput:
    """Food data provenance summary from a match."""
    has_barcode: bool = False
    trust_tier: str = "estimated"  # verified, official, community, estimated
    serving_certainty: float = 0.5  # 0.0-1.0
    quality_flag_count: int = 0
    has_carbs: bool = True
    has_calories: bool = True
    has_fat: bool = True
    has_protein: bool = True


@dataclass
class HistoricalMatchInput:
    """Historical match quality summary."""
    match_count: int = 0
    avg_similarity_score: float = 0.0  # 0.0-1.0
    has_peak_delta_data: bool = False
    has_peak_time_data: bool = False
    peak_delta_consistency: Optional[float] = None  # coefficient of variation


@dataclass
class ConfidenceResult:
    """Unified confidence scoring result."""
    overall_score: float  # 0.0-1.0
    tier: str  # low, moderate, high
    components: dict[str, float]  # decomposed scores
    narrative: str
    recommendations: list[str] = field(default_factory=list)


# ── Scoring ──


def _score_food_provenance(fp: FoodProvenanceInput) -> float:
    """Score food data provenance quality (0.0-1.0)."""
    score = 0.5  # baseline

    # Trust tier
    tier_scores = {
        "verified": 0.35,
        "official": 0.25,
        "community": 0.0,
        "estimated": -0.15,
    }
    score += tier_scores.get(fp.trust_tier, -0.1)

    # Barcode = exact match
    if fp.has_barcode:
        score += 0.15

    # Serving certainty
    score += fp.serving_certainty * 0.1

    # Quality flags penalize
    score -= fp.quality_flag_count * 0.08

    # Nutrient completeness
    nutrient_count = sum([fp.has_carbs, fp.has_calories, fp.has_fat, fp.has_protein])
    score += (nutrient_count / 4) * 0.1

    return max(0.0, min(1.0, score))


def _score_historical_match(hm: HistoricalMatchInput) -> float:
    """Score historical match quality (0.0-1.0).

    Returns 0.0 if no matches, meaning the forecast is purely
    rules-based with no user history to draw on.
    """
    if hm.match_count == 0:
        return 0.0

    score = 0.0

    # Sample size (more matches = more reliable)
    # 3 matches = 0.3, 10+ matches = 1.0
    sample_score = min(hm.match_count / 10.0, 1.0)
    score += sample_score * 0.4

    # Similarity of matches (higher = more reliable)
    score += hm.avg_similarity_score * 0.25

    # Peak delta consistency (lower CV = more consistent)
    if hm.peak_delta_consistency is not None:
        # CV <= 0.2 is very consistent, CV >= 0.8 is very inconsistent
        consistency_score = max(0.0, 1.0 - hm.peak_delta_consistency)
        score += consistency_score * 0.2

    # CGM data availability
    data_completeness = 0
    if hm.has_peak_delta_data:
        data_completeness += 0.075
    if hm.has_peak_time_data:
        data_completeness += 0.075
    score += data_completeness

    return max(0.0, min(1.0, score))


# ── Public API ──


def compute_confidence(
    food_provenance: Optional[FoodProvenanceInput] = None,
    historical_match: Optional[HistoricalMatchInput] = None,
) -> ConfidenceResult:
    """Compute unified confidence score from all available data dimensions.

    Args:
        food_provenance: Quality of the food nutrition data source.
        historical_match: Quality of the historical meal matching.

    Returns:
        ConfidenceResult with overall score, tier, components, and narrative.
    """
    fp = food_provenance or FoodProvenanceInput()
    hm = historical_match or HistoricalMatchInput()

    # Score each dimension
    food_score = _score_food_provenance(fp)
    history_score = _score_historical_match(hm)

    # Combined score
    weights = {"food": 0.4, "history": 0.6}
    overall = food_score * weights["food"] + history_score * weights["history"]

    # Determine tier: CONFIDENCE_TIERS is sorted descending (high→low first match wins)
    tier = "low"
    tier_narrative = CONFIDENCE_TIERS[-1][2]  # default to low
    for threshold, t, tn in CONFIDENCE_TIERS:
        if overall >= threshold:
            tier = t
            tier_narrative = tn
            break

    # Build narrative
    parts = [tier_narrative]

    if hm.match_count > 0:
        parts.append(
            f"Based on {hm.match_count} similar meal{'s' if hm.match_count != 1 else ''} "
            f"in your history (avg similarity: {hm.avg_similarity_score:.0%})."
        )
    else:
        parts.append(
            "No exact matches found in your history — this forecast uses "
            "general nutritional patterns rather than your personal data."
        )

    if fp.has_barcode:
        parts.append("Food data is barcode-verified.")
    elif fp.trust_tier == "estimated":
        parts.append("Nutrition data is estimated — actual values may differ.")

    narrative = " ".join(parts)

    # Build recommendations
    recommendations = []
    if overall < 0.5:
        recommendations.append("Log this meal to improve future forecasts.")
    if hm.match_count < 3 and hm.match_count > 0:
        recommendations.append("More data points will improve the reliability of these estimates.")
    if fp.quality_flag_count > 0:
        recommendations.append(f"Food data has {fp.quality_flag_count} quality flags — nutrition values may be approximate.")

    return ConfidenceResult(
        overall_score=round(overall, 3),
        tier=tier,
        components={
            "food_provenance": round(food_score, 3),
            "historical_match": round(history_score, 3),
        },
        narrative=narrative,
        recommendations=recommendations,
    )


def score_and_narrate(
    match_count: int,
    avg_similarity: float = 0.0,
    has_barcode: bool = False,
    trust_tier: str = "estimated",
    quality_flags: int = 0,
    has_cgm_data: bool = False,
) -> ConfidenceResult:
    """Convenience function for the companion pipeline.

    Accepts flat parameters (most common case) and produces
    a full ConfidenceResult.
    """
    return compute_confidence(
        food_provenance=FoodProvenanceInput(
            has_barcode=has_barcode,
            trust_tier=trust_tier,
            quality_flag_count=quality_flags,
        ),
        historical_match=HistoricalMatchInput(
            match_count=match_count,
            avg_similarity_score=avg_similarity,
            has_peak_delta_data=has_cgm_data,
            has_peak_time_data=has_cgm_data,
        ),
    )