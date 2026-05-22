"""Food provenance and confidence model.

Represents how trustworthy each resolved food item is so downstream forecast
confidence can be evidence-based rather than implied precision.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class SourceTrustTier(str, Enum):
    """Trust tier for food data sources."""
    VERIFIED = "verified"      # User-confirmed or curated
    OFFICIAL = "official"      # Brand/manufacturer verified
    COMMUNITY = "community"    # User contributions
    ESTIMATED = "estimated"    # Derived/imputed


class QualityFlag(str, Enum):
    """Quality issues that may affect food data reliability."""
    MISSING_CARBS = "missing_carbs"
    MISSING_SERVING_GRAMS = "missing_serving_grams"
    MISSING_CALORIES = "missing_calories"
    BARCODE_ABSENT = "barcode_absent"
    CONFLICTING_DUPLICATE = "conflicting_duplicate_barcode"
    IMPLAUSIBLE_MACROS = "implausible_macro_totals"
    COMMUNITY_ONLY = "community_only_row"
    STALE_SOURCE = "stale_source_row"


@dataclass
class FoodProvenance:
    """Provenance information for a resolved food item.
    
    Tracks the trust level and quality issues for food data so downstream
    systems can adjust confidence accordingly.
    """
    
    source_name: str
    source_id: Optional[str] = None
    barcode_match: bool = False
    serving_certainty: float = 0.5  # 0.0 to 1.0
    source_trust_tier: SourceTrustTier = SourceTrustTier.ESTIMATED
    quality_flags: list[QualityFlag] = field(default_factory=list)
    last_updated: Optional[str] = None
    
    def confidence_score(self) -> float:
        """Compute a confidence score from provenance fields.
        
        Returns:
            Confidence score from 0.0 to 1.0
        """
        score = 0.5  # Base score
        
        # Barcode match boost
        if self.barcode_match:
            score += 0.2
        
        # Trust tier adjustments
        tier_scores = {
            SourceTrustTier.VERIFIED: 0.3,
            SourceTrustTier.OFFICIAL: 0.2,
            SourceTrustTier.COMMUNITY: -0.2,
            SourceTrustTier.ESTIMATED: -0.3,
        }
        score += tier_scores.get(self.source_trust_tier, 0)
        
        # Serving certainty contribution
        score += self.serving_certainty * 0.1
        
        # Quality flag penalties (stronger penalty)
        score -= len(self.quality_flags) * 0.1
        
        # Clamp to valid range
        return max(0.0, min(1.0, score))
    
    def is_reliable(self) -> bool:
        """Return True if provenance indicates reliable data."""
        return self.confidence_score() >= 0.7


def compute_provenance(
    source: str,
    barcode: Optional[str],
    query_barcode: Optional[str],
    serving_weight: Optional[float],
    quality_issues: Optional[list[str]] = None,
) -> FoodProvenance:
    """Compute provenance for a resolved food item.
    
    Args:
        source: Source name (e.g., "openfoodfacts", "user_foods")
        barcode: The product's barcode
        query_barcode: The barcode used for lookup (for match detection)
        serving_weight: Serving weight in grams if available
        quality_issues: List of quality issue identifiers
        
    Returns:
        FoodProvenance instance with computed fields
    """
    quality_flags = []
    if quality_issues:
        for issue in quality_issues:
            try:
                quality_flags.append(QualityFlag(issue))
            except ValueError:
                pass  # Unknown flag, skip
    
    # Determine serving certainty
    serving_certainty = 0.5
    if serving_weight is None:
        serving_certainty = 0.2
        quality_flags.append(QualityFlag.MISSING_SERVING_GRAMS)
    elif serving_weight > 0:
        serving_certainty = 0.9
    
    # Determine trust tier
    if source == "user_foods":
        tier = SourceTrustTier.VERIFIED
    elif source == "openfoodfacts":
        if any(f.value == "community_only_row" for f in quality_flags):
            tier = SourceTrustTier.COMMUNITY
        else:
            tier = SourceTrustTier.OFFICIAL
    else:
        tier = SourceTrustTier.ESTIMATED
    
    return FoodProvenance(
        source_name=source,
        source_id=barcode,
        barcode_match=barcode is not None and barcode == query_barcode,
        serving_certainty=serving_certainty,
        source_trust_tier=tier,
        quality_flags=quality_flags,
    )