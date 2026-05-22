"""Tests for serving normalization helper."""

import pytest

from app.food.models import OpenFoodFactsProduct
from app.food.serving_normalizer import (
    NormalizedQuantity,
    normalize_quantity,
    normalize_from_off,
    DEFAULT_SERVING_WEIGHTS,
)


class TestNormalizedQuantity:
    """Tests for NormalizedQuantity dataclass."""

    def test_confidence_clamped_low(self):
        """Confidence is clamped to 0.0 minimum."""
        nq = NormalizedQuantity(quantity_g=100, confidence=-0.5)
        assert nq.confidence == 0.0

    def test_confidence_clamped_high(self):
        """Confidence is clamped to 1.0 maximum."""
        nq = NormalizedQuantity(quantity_g=100, confidence=1.5)
        assert nq.confidence == 1.0


class TestNormalizeQuantity:
    """Tests for normalize_quantity function."""

    def test_grams_direct(self):
        """Gram units pass through unchanged."""
        result = normalize_quantity(50, "g")
        assert result.quantity_g == 50
        assert result.confidence == 1.0

    def test_kg_conversion(self):
        """Kilograms convert to grams correctly."""
        result = normalize_quantity(2, "kg")
        assert result.quantity_g == 2000
        assert result.confidence == 1.0

    def test_milliliters_default(self):
        """Milliliters use 1g/ml default."""
        result = normalize_quantity(240, "ml")
        assert result.quantity_g == 240
        assert result.confidence == 0.8

    def test_cup_conversion(self):
        """Cups convert using default weight."""
        result = normalize_quantity(1, "cup")
        assert result.quantity_g == DEFAULT_SERVING_WEIGHTS["cup"]
        assert result.confidence == 0.8

    def test_slice_conversion(self):
        """Slices use default weight."""
        result = normalize_quantity(2, "slice")
        assert result.quantity_g == 2 * DEFAULT_SERVING_WEIGHTS["slice"]
        assert result.confidence == 0.7

    def test_unknown_unit_fallback(self):
        """Unknown units use 100g default with low confidence."""
        result = normalize_quantity(3, "pinch")
        assert result.quantity_g == 300  # 3 * 100 default
        assert result.confidence == 0.3
        assert "Unknown unit" in (result.notes or "")


class TestNormalizeFromOFF:
    """Tests for normalize_from_off function."""

    def test_product_with_serving_quantity(self):
        """Use product serving_quantity when available."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Test Bread",
            serving_quantity=35.0,
        )
        result = normalize_from_off(product, 2, "slice")
        assert result.quantity_g == 70.0

    def test_bread_product_slice_detection(self):
        """Bread products get high confidence for slices."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Whole Wheat Bread",
            serving_quantity=35.0,
        )
        result = normalize_from_off(product, 2, "slice")
        assert result.confidence == 0.95
        assert "Bread slice" in result.notes

    def test_falls_back_without_product_data(self):
        """Fall back to defaults when product has no serving data."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Mystery Food",
        )
        result = normalize_from_off(product, 2, "piece")
        # Falls back to default piece weight
        assert result.quantity_g == 2 * DEFAULT_SERVING_WEIGHTS["piece"]


class TestRealWorldExamples:
    """Tests using real-world-like examples."""

    def test_eggs_example(self):
        """Normalize 2 eggs (large ~50g each)."""
        # Eggs typically sold as units
        result = normalize_quantity(2, "piece")
        assert result.quantity_g == 100.0  # 2 * 50g default

    def test_bread_slice_example(self):
        """Normalize 2 bread slices using product data."""
        product = OpenFoodFactsProduct(
            code="0544310000000",
            product_name="Sandwich Bread",
            serving_quantity=35.0,
        )
        result = normalize_from_off(product, 2, "slice")
        assert result.quantity_g == 70.0
        assert result.confidence >= 0.9

    def test_liquid_ml_example(self):
        """Normalize 250ml of liquid."""
        result = normalize_quantity(250, "ml")
        assert result.quantity_g == 250.0  # 1g/ml approximation