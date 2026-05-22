"""Tests for food quality flags and duplicate detection.

Exercises:
1. Quality flag assessment for individual food items
2. Quality flag aggregation in meal composition
3. Duplicate detection heuristics
4. Confidence impact from quality flags
"""

import pytest
import pytest_asyncio

from app.food.provenance import (
    QualityFlag,
    SourceTrustTier,
    FoodProvenance,
    assess_food_quality,
    check_duplicate_candidates,
    compute_provenance,
    _normalize_name,
    _names_similar,
    _brands_similar,
    _servings_similar,
    _nutrient_conflicts,
)


# ──────────────────────────────────────────────
# Quality Flag Assessment Tests
# ──────────────────────────────────────────────


class TestAssessFoodQuality:
    """Tests for the assess_food_quality function."""

    def test_clean_food_no_flags(self):
        """A complete, well-sourced food item gets no quality flags."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
            protein=5.0,
            fat=2.0,
        )
        assert flags == []

    def test_missing_carbs_flag(self):
        """Missing carbs triggers MISSING_CARBS flag."""
        flags = assess_food_quality(
            carbs=None,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
        )
        assert QualityFlag.MISSING_CARBS in flags

    def test_missing_calories_flag(self):
        """Missing calories triggers MISSING_CALORIES flag."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=None,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
        )
        assert QualityFlag.MISSING_CALORIES in flags

    def test_missing_serving_weight_flag(self):
        """Missing serving weight triggers MISSING_SERVING_GRAMS flag."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=None,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
        )
        assert QualityFlag.MISSING_SERVING_GRAMS in flags

    def test_no_barcode_flag(self):
        """Missing barcode triggers BARCODE_ABSENT flag."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode=None,
            source="openfoodfacts",
        )
        assert QualityFlag.BARCODE_ABSENT in flags

    def test_ambiguous_serving_unit_flag(self):
        """Ambiguous serving units trigger AMBIGUOUS_SERVING_UNIT flag."""
        for unit in ("serving", "unit", "portion"):
            flags = assess_food_quality(
                carbs=20.0,
                calories=100.0,
                serving_weight=100.0,
                serving_unit=unit,
                barcode="123456789",
                source="openfoodfacts",
            )
            assert QualityFlag.AMBIGUOUS_SERVING_UNIT in flags, f"Failed for unit={unit}"

    def test_implausible_macros_flag(self):
        """Implausible macro totals trigger IMPLAUSIBLE_MACROS flag."""
        # 20g carbs * 4 + 5g protein * 4 + 2g fat * 9 = 128 cal, but we say 500
        flags = assess_food_quality(
            carbs=20.0,
            calories=500.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
            protein=5.0,
            fat=2.0,
        )
        assert QualityFlag.IMPLAUSIBLE_MACROS in flags

    def test_reasonable_macros_no_flag(self):
        """Reasonable macro totals don't trigger IMPLAUSIBLE_MACROS."""
        # 20g carbs * 4 + 5g protein * 4 + 2g fat * 9 = 128 cal, we say 130
        flags = assess_food_quality(
            carbs=20.0,
            calories=130.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
            protein=5.0,
            fat=2.0,
        )
        assert QualityFlag.IMPLAUSIBLE_MACROS not in flags

    def test_community_only_flag(self):
        """Community source triggers COMMUNITY_ONLY flag."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="community",
        )
        assert QualityFlag.COMMUNITY_ONLY in flags

    def test_stale_source_flag(self):
        """Source older than 2 years triggers STALE_SOURCE flag."""
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
            source_updated_at="2020-01-01T00:00:00Z",
        )
        assert QualityFlag.STALE_SOURCE in flags

    def test_recent_source_no_stale_flag(self):
        """Recent source doesn't trigger STALE_SOURCE."""
        from datetime import datetime, timezone, timedelta
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        flags = assess_food_quality(
            carbs=20.0,
            calories=100.0,
            serving_weight=100.0,
            serving_unit="g",
            barcode="123456789",
            source="openfoodfacts",
            source_updated_at=recent,
        )
        assert QualityFlag.STALE_SOURCE not in flags

    def test_multiple_flags_accumulate(self):
        """Multiple quality issues accumulate in the flags list."""
        flags = assess_food_quality(
            carbs=None,
            calories=None,
            serving_weight=None,
            serving_unit="serving",
            barcode=None,
            source="community",
        )
        assert QualityFlag.MISSING_CARBS in flags
        assert QualityFlag.MISSING_CALORIES in flags
        assert QualityFlag.MISSING_SERVING_GRAMS in flags
        assert QualityFlag.BARCODE_ABSENT in flags
        assert QualityFlag.AMBIGUOUS_SERVING_UNIT in flags
        assert QualityFlag.COMMUNITY_ONLY in flags
        assert len(flags) == 6


# ──────────────────────────────────────────────
# FoodProvenance Quality Method Tests
# ──────────────────────────────────────────────


class TestFoodProvenanceQuality:
    """Tests for FoodProvenance quality-related methods."""

    def test_has_critical_quality_issue_missing_carbs(self):
        """MISSING_CARBS is a critical quality issue."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[QualityFlag.MISSING_CARBS],
        )
        assert prov.has_critical_quality_issue() is True

    def test_has_critical_quality_issue_implausible(self):
        """IMPLAUSIBLE_MACROS is a critical quality issue."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[QualityFlag.IMPLAUSIBLE_MACROS],
        )
        assert prov.has_critical_quality_issue() is True

    def test_has_critical_quality_issue_conflicting(self):
        """CONFLICTING_DUPLICATE is a critical quality issue."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[QualityFlag.CONFLICTING_DUPLICATE],
        )
        assert prov.has_critical_quality_issue() is True

    def test_no_critical_quality_issue(self):
        """Non-critical flags don't trigger has_critical_quality_issue."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[QualityFlag.BARCODE_ABSENT, QualityFlag.COMMUNITY_ONLY],
        )
        assert prov.has_critical_quality_issue() is False

    def test_no_flags_no_critical_issue(self):
        """Clean provenance has no critical issues."""
        prov = FoodProvenance(source_name="test")
        assert prov.has_critical_quality_issue() is False

    def test_quality_summary_clean(self):
        """Clean provenance returns 'clean' summary."""
        prov = FoodProvenance(source_name="test")
        assert prov.quality_summary() == "clean"

    def test_quality_summary_with_flags(self):
        """Provenance with flags returns comma-separated flag values."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[QualityFlag.MISSING_CARBS, QualityFlag.BARCODE_ABSENT],
        )
        summary = prov.quality_summary()
        assert "missing_carbs" in summary
        assert "barcode_absent" in summary

    def test_confidence_score_penalized_by_flags(self):
        """More quality flags = lower confidence score."""
        clean = FoodProvenance(
            source_name="test",
            barcode_match=True,
            source_trust_tier=SourceTrustTier.OFFICIAL,
            serving_certainty=0.9,
        )
        dirty = FoodProvenance(
            source_name="test",
            barcode_match=True,
            source_trust_tier=SourceTrustTier.OFFICIAL,
            serving_certainty=0.9,
            quality_flags=[
                QualityFlag.MISSING_CARBS,
                QualityFlag.BARCODE_ABSENT,
                QualityFlag.COMMUNITY_ONLY,
            ],
        )
        assert clean.confidence_score() > dirty.confidence_score()

    def test_is_reliable_with_many_flags(self):
        """Too many quality flags makes provenance unreliable."""
        prov = FoodProvenance(
            source_name="test",
            quality_flags=[
                QualityFlag.MISSING_CARBS,
                QualityFlag.MISSING_CALORIES,
                QualityFlag.MISSING_SERVING_GRAMS,
                QualityFlag.BARCODE_ABSENT,
                QualityFlag.COMMUNITY_ONLY,
            ],
        )
        assert prov.is_reliable() is False


# ──────────────────────────────────────────────
# Duplicate Detection Tests
# ──────────────────────────────────────────────


class TestNormalizeName:
    """Tests for _normalize_name helper."""

    def test_lowercase(self):
        assert _normalize_name("Coca-Cola") == "cocacola"

    def test_hyphen_removed(self):
        assert _normalize_name("Coca-Cola") == "cocacola"

    def test_spaces_preserved(self):
        assert _normalize_name("Oat Milk") == "oat milk"

    def test_strip_whitespace(self):
        assert _normalize_name("  oatmeal  ") == "oatmeal"

    def test_remove_punctuation(self):
        assert _normalize_name("Oatmeal, Organic!") == "oatmeal organic"

    def test_collapse_spaces(self):
        assert _normalize_name("oat   meal") == "oat meal"

    def test_empty_string(self):
        assert _normalize_name("") == ""


class TestNamesSimilar:
    """Tests for _names_similar helper."""

    def test_exact_match(self):
        assert _names_similar("Oatmeal", "oatmeal") is True

    def test_contains(self):
        assert _names_similar("Coca-Cola", "Coca-Cola Classic") is True

    def test_not_similar(self):
        assert _names_similar("Oatmeal", "Corn Flakes") is False

    def test_empty_name(self):
        assert _names_similar("", "Oatmeal") is False


class TestBrandsSimilar:
    """Tests for _brands_similar helper."""

    def test_same_brand(self):
        assert _brands_similar("Nestle", "Nestle") is True

    def test_case_insensitive(self):
        assert _brands_similar("Nestle", "nestle") is True

    def test_both_missing(self):
        assert _brands_similar(None, None) is True

    def test_one_missing(self):
        assert _brands_similar("Nestle", None) is False

    def test_different(self):
        assert _brands_similar("Nestle", "Kellogg's") is False


class TestServingsSimilar:
    """Tests for _servings_similar helper."""

    def test_same_numeric(self):
        assert _servings_similar(100.0, 100.0) is True

    def test_within_threshold(self):
        assert _servings_similar(100.0, 105.0) is True  # 5% diff

    def test_outside_threshold(self):
        assert _servings_similar(100.0, 150.0) is False  # 50% diff

    def test_both_none(self):
        assert _servings_similar(None, None) is True

    def test_one_none(self):
        assert _servings_similar(100.0, None) is False

    def test_string_match(self):
        assert _servings_similar("30 g", "30 g") is True

    def test_string_mismatch(self):
        assert _servings_similar("30 g", "50 g") is False


class TestNutrientConflicts:
    """Tests for _nutrient_conflicts helper."""

    def test_no_conflicts(self):
        a = {"carbs_per_100g": 20.0, "protein_per_100g": 5.0, "fat_per_100g": 2.0, "calories_per_100g": 130.0}
        b = {"carbs_per_100g": 20.0, "protein_per_100g": 5.0, "fat_per_100g": 2.0, "calories_per_100g": 130.0}
        assert _nutrient_conflicts(a, b) == []

    def test_carbs_conflict(self):
        a = {"carbs_per_100g": 20.0, "protein_per_100g": 5.0, "fat_per_100g": 2.0, "calories_per_100g": 130.0}
        b = {"carbs_per_100g": 50.0, "protein_per_100g": 5.0, "fat_per_100g": 2.0, "calories_per_100g": 130.0}
        conflicts = _nutrient_conflicts(a, b)
        assert "carbs_per_100g" in conflicts

    def test_missing_values_skipped(self):
        a = {"carbs_per_100g": 20.0, "protein_per_100g": None}
        b = {"carbs_per_100g": 20.0, "protein_per_100g": 5.0}
        assert _nutrient_conflicts(a, b) == []

    def test_both_zero_skipped(self):
        a = {"carbs_per_100g": 0.0, "fat_per_100g": 0.0}
        b = {"carbs_per_100g": 0.0, "fat_per_100g": 0.0}
        assert _nutrient_conflicts(a, b) == []


class TestCheckDuplicateCandidates:
    """Tests for the check_duplicate_candidates function."""

    def test_no_duplicates(self):
        """Distinct items produce no duplicates."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111", "carbs_per_100g": 60.0,
             "protein_per_100g": 10.0, "fat_per_100g": 5.0, "calories_per_100g": 300.0,
             "source": "openfoodfacts", "serving_size": "100 g"},
            {"name": "Corn Flakes", "brand": "Kellogg's", "barcode": "222", "carbs_per_100g": 85.0,
             "protein_per_100g": 7.0, "fat_per_100g": 1.0, "calories_per_100g": 350.0,
             "source": "openfoodfacts", "serving_size": "100 g"},
        ]
        result = check_duplicate_candidates(items)
        assert result == []

    def test_same_barcode_conflicting_nutrients(self):
        """Same barcode with conflicting nutrients = CONFLICTING_DUPLICATE."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111", "carbs_per_100g": 60.0,
             "protein_per_100g": 10.0, "fat_per_100g": 5.0, "calories_per_100g": 300.0,
             "source": "openfoodfacts", "serving_size": "100 g"},
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111", "carbs_per_100g": 90.0,
             "protein_per_100g": 10.0, "fat_per_100g": 5.0, "calories_per_100g": 300.0,
             "source": "usda", "serving_size": "100 g"},
        ]
        result = check_duplicate_candidates(items)
        assert len(result) == 1
        assert result[0][2] == QualityFlag.CONFLICTING_DUPLICATE

    def test_same_barcode_consistent_nutrients(self):
        """Same barcode with consistent nutrients = no duplicate."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111", "carbs_per_100g": 60.0,
             "protein_per_100g": 10.0, "fat_per_100g": 5.0, "calories_per_100g": 300.0,
             "source": "openfoodfacts", "serving_size": "100 g"},
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111", "carbs_per_100g": 61.0,
             "protein_per_100g": 10.0, "fat_per_100g": 5.0, "calories_per_100g": 302.0,
             "source": "usda", "serving_size": "100 g"},
        ]
        result = check_duplicate_candidates(items)
        assert result == []

    def test_near_duplicate_name_brand_serving(self):
        """Near-identical name + brand + serving = NEAR_DUPLICATE_NAME."""
        items = [
            {"name": "Coca-Cola Classic", "brand": "Coca-Cola", "barcode": "111",
             "carbs_per_100g": 10.6, "protein_per_100g": 0.0, "fat_per_100g": 0.0,
             "calories_per_100g": 42.0, "source": "openfoodfacts", "serving_size": "330 ml"},
            {"name": "Coca-Cola", "brand": "Coca-Cola", "barcode": "222",
             "carbs_per_100g": 10.6, "protein_per_100g": 0.0, "fat_per_100g": 0.0,
             "calories_per_100g": 42.0, "source": "usda", "serving_size": "330 ml"},
        ]
        result = check_duplicate_candidates(items)
        assert len(result) == 1
        assert result[0][2] == QualityFlag.NEAR_DUPLICATE_NAME

    def test_normalized_name_collision_across_sources(self):
        """Same normalized name from different sources = NORMALIZED_NAME_COLLISION."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111",
             "carbs_per_100g": 60.0, "protein_per_100g": 10.0, "fat_per_100g": 5.0,
             "calories_per_100g": 300.0, "source": "openfoodfacts", "serving_size": "100 g"},
            {"name": "Oatmeal!", "brand": None, "barcode": None,
             "carbs_per_100g": 58.0, "protein_per_100g": 9.0, "fat_per_100g": 4.5,
             "calories_per_100g": 290.0, "source": "usda", "serving_size": None},
        ]
        result = check_duplicate_candidates(items)
        assert len(result) == 1
        assert result[0][2] == QualityFlag.NORMALIZED_NAME_COLLISION

    def test_same_source_no_collision(self):
        """Same normalized name from the SAME source is not a collision."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111",
             "carbs_per_100g": 60.0, "protein_per_100g": 10.0, "fat_per_100g": 5.0,
             "calories_per_100g": 300.0, "source": "openfoodfacts", "serving_size": "100 g"},
            {"name": "Oatmeal!", "brand": None, "barcode": None,
             "carbs_per_100g": 58.0, "protein_per_100g": 9.0, "fat_per_100g": 4.5,
             "calories_per_100g": 290.0, "source": "openfoodfacts", "serving_size": None},
        ]
        result = check_duplicate_candidates(items)
        assert result == []

    def test_empty_items(self):
        """Empty list produces no duplicates."""
        assert check_duplicate_candidates([]) == []

    def test_single_item(self):
        """Single item produces no duplicates."""
        items = [
            {"name": "Oatmeal", "brand": "Quaker", "barcode": "111",
             "carbs_per_100g": 60.0, "protein_per_100g": 10.0, "fat_per_100g": 5.0,
             "calories_per_100g": 300.0, "source": "openfoodfacts", "serving_size": "100 g"},
        ]
        assert check_duplicate_candidates(items) == []


# ──────────────────────────────────────────────
# Compute Provenance with Quality Assessment
# ──────────────────────────────────────────────


class TestComputeProvenanceWithQuality:
    """Tests for compute_provenance with the new quality assessment parameters."""

    def test_auto_flags_from_nutrient_data(self):
        """compute_provenance auto-assesses quality from nutrient fields."""
        prov = compute_provenance(
            source="openfoodfacts",
            barcode=None,
            query_barcode=None,
            serving_weight=None,
            carbs=None,
            calories=100.0,
        )
        assert QualityFlag.MISSING_CARBS in prov.quality_flags
        assert QualityFlag.MISSING_SERVING_GRAMS in prov.quality_flags
        assert QualityFlag.BARCODE_ABSENT in prov.quality_flags

    def test_no_redundant_flags(self):
        """Legacy quality_issues flags are not duplicated by auto-assessment."""
        prov = compute_provenance(
            source="openfoodfacts",
            barcode="123",
            query_barcode="123",
            serving_weight=100.0,
            quality_issues=["missing_carbs"],
            carbs=None,
            calories=100.0,
        )
        # Should have missing_carbs only once
        flag_values = [f.value for f in prov.quality_flags]
        assert flag_values.count("missing_carbs") == 1

    def test_clean_food_no_auto_flags(self):
        """Complete food data produces no auto-assessed flags."""
        prov = compute_provenance(
            source="openfoodfacts",
            barcode="123456789",
            query_barcode="123456789",
            serving_weight=100.0,
            carbs=20.0,
            calories=130.0,
            protein=5.0,
            fat=2.0,
        )
        assert prov.quality_flags == []

    def test_user_foods_trust_tier(self):
        """User foods get VERIFIED trust tier."""
        prov = compute_provenance(
            source="user_foods",
            barcode=None,
            query_barcode=None,
            serving_weight=None,
        )
        assert prov.source_trust_tier == SourceTrustTier.VERIFIED

    def test_openfoodfacts_local_trust_tier(self):
        """openfoodfacts_local gets OFFICIAL trust tier."""
        prov = compute_provenance(
            source="openfoodfacts_local",
            barcode="123",
            query_barcode="123",
            serving_weight=100.0,
        )
        assert prov.source_trust_tier == SourceTrustTier.OFFICIAL