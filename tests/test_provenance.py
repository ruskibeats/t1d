"""Tests for food provenance and confidence model."""

import pytest

from app.food.provenance import (
    FoodProvenance,
    SourceTrustTier,
    QualityFlag,
    compute_provenance,
)


class TestFoodProvenance:
    """Tests for FoodProvenance dataclass."""

    def test_confidence_score_base(self):
        """Base confidence with no adjustments."""
        p = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.ESTIMATED,
            serving_certainty=0.5,
        )
        assert 0.0 <= p.confidence_score() <= 1.0

    def test_confidence_score_with_barcode_match(self):
        """Barcode match increases confidence."""
        p = FoodProvenance(
            source_name="test",
            barcode_match=True,
            source_trust_tier=SourceTrustTier.OFFICIAL,
        )
        score = p.confidence_score()
        assert score >= 0.7

    def test_confidence_score_verified_tier(self):
        """Verified source gets high confidence."""
        p = FoodProvenance(
            source_name="user",
            source_trust_tier=SourceTrustTier.VERIFIED,
            barcode_match=True,
            serving_certainty=0.9,
        )
        assert p.confidence_score() >= 0.8

    def test_confidence_score_with_quality_flags(self):
        """Quality flags reduce confidence."""
        p = FoodProvenance(
            source_name="test",
            source_trust_tier=SourceTrustTier.ESTIMATED,
            quality_flags=[QualityFlag.MISSING_CARBS, QualityFlag.MISSING_CALORIES, QualityFlag.IMPLAUSIBLE_MACROS],
        )
        assert p.confidence_score() < 0.5

    def test_is_reliable_high_confidence(self):
        """High confidence provenance is reliable."""
        p = FoodProvenance(
            source_name="user",
            source_trust_tier=SourceTrustTier.VERIFIED,
            barcode_match=True,
        )
        assert p.is_reliable() is True

    def test_is_reliable_low_confidence(self):
        """Low confidence provenance is not reliable."""
        p = FoodProvenance(
            source_name="community",
            source_trust_tier=SourceTrustTier.COMMUNITY,
            quality_flags=[QualityFlag.IMPLAUSIBLE_MACROS],
        )
        assert p.is_reliable() is False


class TestComputeProvenance:
    """Tests for compute_provenance function."""

    def test_user_food_verified(self):
        """User foods get verified tier."""
        p = compute_provenance(
            source="user_foods",
            barcode="1234567890123",
            query_barcode="1234567890123",
            serving_weight=50.0,
        )
        assert p.source_trust_tier == SourceTrustTier.VERIFIED
        assert p.barcode_match is True
        assert p.serving_certainty == 0.9

    def test_off_barcode_match(self):
        """OFF match detected when barcodes equal."""
        p = compute_provenance(
            source="openfoodfacts",
            barcode="0544310000000",
            query_barcode="0544310000000",
            serving_weight=35.0,
        )
        assert p.barcode_match is True
        assert p.source_trust_tier == SourceTrustTier.OFFICIAL

    def test_off_no_barcode(self):
        """OFF without barcode gets default values."""
        p = compute_provenance(
            source="openfoodfacts",
            barcode=None,
            query_barcode="0544310000000",
            serving_weight=100.0,
        )
        assert p.barcode_match is False
        assert p.source_trust_tier == SourceTrustTier.OFFICIAL

    def test_quality_flags_parsed(self):
        """Quality flags are parsed correctly."""
        p = compute_provenance(
            source="openfoodfacts",
            barcode="123",
            query_barcode="123",
            serving_weight=50.0,
            quality_issues=["missing_carbs", "missing_calories"],
        )
        assert QualityFlag.MISSING_CARBS in p.quality_flags
        assert QualityFlag.MISSING_CALORIES in p.quality_flags

    def test_missing_serving_weight(self):
        """Missing serving weight detected."""
        p = compute_provenance(
            source="test",
            barcode="123",
            query_barcode="123",
            serving_weight=None,
        )
        assert QualityFlag.MISSING_SERVING_GRAMS in p.quality_flags


class TestRealWorldExamples:
    """Tests using real-world-like examples."""

    def test_bread_slice_provenance(self):
        """Bread slice with barcode match."""
        p = compute_provenance(
            source="openfoodfacts",
            barcode="0544310000000",
            query_barcode="0544310000000",
            serving_weight=35.0,
        )
        assert p.barcode_match is True
        assert p.source_trust_tier == SourceTrustTier.OFFICIAL
        assert p.is_reliable() is True

    def test_egg_without_barcode(self):
        """Eggs without barcode get estimated provenance."""
        p = compute_provenance(
            source="openfoodfacts",
            barcode=None,
            query_barcode=None,
            serving_weight=50.0,
        )
        assert p.barcode_match is False
        assert p.source_trust_tier == SourceTrustTier.OFFICIAL