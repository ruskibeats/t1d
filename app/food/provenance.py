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
    AMBIGUOUS_SERVING_UNIT = "ambiguous_serving_unit"
    NEAR_DUPLICATE_NAME = "near_duplicate_name"
    NORMALIZED_NAME_COLLISION = "normalized_name_collision"


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

    def has_critical_quality_issue(self) -> bool:
        """Return True if any critical quality flags are present."""
        critical = {
            QualityFlag.MISSING_CARBS,
            QualityFlag.IMPLAUSIBLE_MACROS,
            QualityFlag.CONFLICTING_DUPLICATE,
        }
        return bool(critical.intersection(set(self.quality_flags)))

    def quality_summary(self) -> str:
        """Return a human-readable summary of quality flags."""
        if not self.quality_flags:
            return "clean"
        return ", ".join(f.value for f in self.quality_flags)


# ──────────────────────────────────────────────
# Quality flag computation
# ──────────────────────────────────────────────


def assess_food_quality(
    carbs: float | None,
    calories: float | None,
    serving_weight: float | None,
    serving_unit: str | None,
    barcode: str | None,
    source: str,
    source_updated_at: str | None = None,
    protein: float | None = None,
    fat: float | None = None,
) -> list[QualityFlag]:
    """Assess quality flags for a resolved food item.

    Evaluates nutrient completeness, plausibility, and source freshness.

    Args:
        carbs: Carbs per 100g.
        calories: Calories per 100g.
        serving_weight: Serving weight in grams.
        serving_unit: Unit string (g, ml, serving, etc.).
        barcode: Product barcode if available.
        source: Data source name.
        source_updated_at: ISO timestamp of last source update.
        protein: Protein per 100g (for plausibility checks).
        fat: Fat per 100g (for plausibility checks).

    Returns:
        List of QualityFlag values.
    """
    flags: list[QualityFlag] = []

    if carbs is None:
        flags.append(QualityFlag.MISSING_CARBS)
    if calories is None:
        flags.append(QualityFlag.MISSING_CALORIES)
    if serving_weight is None:
        flags.append(QualityFlag.MISSING_SERVING_GRAMS)
    if not barcode:
        flags.append(QualityFlag.BARCODE_ABSENT)
    if serving_unit and serving_unit.lower() in ("serving", "unit", "portion"):
        flags.append(QualityFlag.AMBIGUOUS_SERVING_UNIT)

    # Implausible macro totals: calories should be roughly 4*carbs + 4*protein + 9*fat
    if calories is not None and carbs is not None and protein is not None and fat is not None:
        estimated_cal = (carbs * 4) + (protein * 4) + (fat * 9)
        if estimated_cal > 0 and abs(estimated_cal - calories) / estimated_cal > 0.5:
            flags.append(QualityFlag.IMPLAUSIBLE_MACROS)

    if source in ("openfoodfacts_community", "community"):
        flags.append(QualityFlag.COMMUNITY_ONLY)

    # Stale source (older than 2 years)
    if source_updated_at:
        from datetime import datetime, timezone
        try:
            updated = datetime.fromisoformat(source_updated_at.replace("Z", "+00:00"))
            age_days = (datetime.now(timezone.utc) - updated).days
            if age_days > 730:
                flags.append(QualityFlag.STALE_SOURCE)
        except (ValueError, TypeError):
            pass

    return flags


# ──────────────────────────────────────────────
# Duplicate detection
# ──────────────────────────────────────────────


def _normalize_name(name: str) -> str:
    """Normalize a food product name for comparison.

    Lowercases, removes non-alphanumeric/non-space characters,
    collapses multiple spaces, and strips leading/trailing whitespace.
    """
    import re
    normalized = name.lower().strip()
    # Remove non-alphanumeric, non-space characters
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
    # Collapse multiple spaces
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def check_duplicate_candidates(
    items: list[dict],
) -> list[tuple[int, int, QualityFlag]]:
    """Check a list of resolved food items for likely duplicates.

    Compares items pairwise using barcode, name, and brand similarity.

    Args:
        items: List of resolved food dicts with keys:
            name, brand, barcode, carbs_per_100g, protein_per_100g,
            fat_per_100g, calories_per_100g, source, serving_size.

    Returns:
        List of (index_a, index_b, flag) tuples indicating duplicate pairs.
    """
    duplicates: list[tuple[int, int, QualityFlag]] = []

    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a = items[i]
            b = items[j]

            # Same barcode with conflicting nutrients
            if a.get("barcode") and b.get("barcode") and a["barcode"] == b["barcode"]:
                conflicts = _nutrient_conflicts(a, b)
                if conflicts:
                    duplicates.append((i, j, QualityFlag.CONFLICTING_DUPLICATE))
                continue

            # Near-identical name + brand + serving size
            name_match = _names_similar(a.get("name", ""), b.get("name", ""))
            brand_match = _brands_similar(a.get("brand", ""), b.get("brand", ""))
            serving_match = _servings_similar(a.get("serving_size"), b.get("serving_size"))

            if name_match and brand_match and serving_match:
                duplicates.append((i, j, QualityFlag.NEAR_DUPLICATE_NAME))
                continue

            # Normalized-name collision across sources
            norm_a = _normalize_name(a.get("name", ""))
            norm_b = _normalize_name(b.get("name", ""))
            if norm_a == norm_b and norm_a:
                source_a = a.get("source", "")
                source_b = b.get("source", "")
                if source_a != source_b:
                    duplicates.append((i, j, QualityFlag.NORMALIZED_NAME_COLLISION))

    return duplicates


def _nutrient_conflicts(a: dict, b: dict) -> list[str]:
    """Check if two items with the same barcode have conflicting nutrients.

    Returns list of conflicting nutrient keys (15% relative difference threshold).
    """
    conflicts = []
    keys = ["carbs_per_100g", "protein_per_100g", "fat_per_100g", "calories_per_100g"]
    threshold = 0.15

    for key in keys:
        val_a = a.get(key)
        val_b = b.get(key)
        if val_a is None or val_b is None:
            continue
        if val_a == 0 and val_b == 0:
            continue
        max_val = max(abs(val_a), abs(val_b))
        if max_val > 0 and abs(val_a - val_b) / max_val > threshold:
            conflicts.append(key)

    return conflicts


def _names_similar(name_a: str, name_b: str) -> bool:
    """Check if two product names are similar enough to be duplicates."""
    norm_a = _normalize_name(name_a)
    norm_b = _normalize_name(name_b)
    if not norm_a or not norm_b:
        return False
    if norm_a == norm_b:
        return True
    if norm_a in norm_b or norm_b in norm_a:
        return True
    return False


def _brands_similar(brand_a: str | None, brand_b: str | None) -> bool:
    """Check if two brand strings are similar (or both missing)."""
    if not brand_a and not brand_b:
        return True
    if not brand_a or not brand_b:
        return False
    return _normalize_name(brand_a) == _normalize_name(brand_b)


def _servings_similar(serving_a, serving_b) -> bool:
    """Check if two serving sizes are similar (or both missing)."""
    if serving_a is None and serving_b is None:
        return True
    if serving_a is None or serving_b is None:
        return False
    try:
        val_a = float(serving_a)
        val_b = float(serving_b)
        if val_a == 0 and val_b == 0:
            return True
        max_val = max(abs(val_a), abs(val_b))
        if max_val > 0 and abs(val_a - val_b) / max_val < 0.2:
            return True
    except (TypeError, ValueError):
        return str(serving_a).strip().lower() == str(serving_b).strip().lower()
    return False


def compute_provenance(
    source: str,
    barcode: str | None,
    query_barcode: str | None,
    serving_weight: float | None,
    quality_issues: list[str] | None = None,
    carbs: float | None = None,
    calories: float | None = None,
    serving_unit: str | None = None,
    source_updated_at: str | None = None,
    protein: float | None = None,
    fat: float | None = None,
) -> FoodProvenance:
    """Compute provenance for a resolved food item.

    Args:
        source: Source name (e.g., "openfoodfacts", "user_foods").
        barcode: The product's barcode.
        query_barcode: The barcode used for lookup (for match detection).
        serving_weight: Serving weight in grams if available.
        quality_issues: Legacy list of quality issue string identifiers.
        carbs: Carbs per 100g (for quality assessment).
        calories: Calories per 100g (for quality assessment).
        serving_unit: Unit string (for quality assessment).
        source_updated_at: ISO timestamp of last source update.
        protein: Protein per 100g (for plausibility checks).
        fat: Fat per 100g (for plausibility checks).

    Returns:
        FoodProvenance instance with computed fields.
    """
    # Start with legacy quality issues if provided
    quality_flags: list[QualityFlag] = []
    if quality_issues:
        for issue in quality_issues:
            try:
                quality_flags.append(QualityFlag(issue))
            except ValueError:
                pass

    # Run comprehensive quality assessment (adds flags not already present)
    assessed = assess_food_quality(
        carbs=carbs,
        calories=calories,
        serving_weight=serving_weight,
        serving_unit=serving_unit,
        barcode=barcode,
        source=source,
        source_updated_at=source_updated_at,
        protein=protein,
        fat=fat,
    )
    existing = set(quality_flags)
    for flag in assessed:
        if flag not in existing:
            quality_flags.append(flag)
            existing.add(flag)

    # Determine serving certainty
    serving_certainty = 0.5
    if serving_weight is None:
        serving_certainty = 0.2
    elif serving_weight > 0:
        serving_certainty = 0.9

    # Determine trust tier
    if source == "user_foods":
        tier = SourceTrustTier.VERIFIED
    elif source in ("openfoodfacts", "openfoodfacts_local"):
        if QualityFlag.COMMUNITY_ONLY in quality_flags:
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
        last_updated=source_updated_at,
    )