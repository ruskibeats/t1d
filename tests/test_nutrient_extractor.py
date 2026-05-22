"""Tests for nutrient extraction helper from OpenFoodFacts products."""

import pytest
from datetime import datetime

from app.food.nutrient_extractor import (
    NutrientProfile,
    extract_nutrients_off,
    extract_nutrients_safe,
)
from app.food.models import OpenFoodFactsProduct


class TestNutrientProfile:
    """Tests for NutrientProfile dataclass."""

    def test_is_complete_with_all_values(self):
        """Profile is complete when all critical nutrients present."""
        profile = NutrientProfile(
            carbs_g=10.0,
            fiber_g=2.0,
            sugars_g=5.0,
            protein_g=3.0,
            fat_g=1.0,
            calories_kcal=100.0,
            serving_weight_g=50.0,
        )
        assert profile.is_complete() is True

    def test_is_complete_with_missing_carbs(self):
        """Profile is incomplete when carbs missing."""
        profile = NutrientProfile(
            carbs_g=None,
            protein_g=3.0,
            fat_g=1.0,
            calories_kcal=100.0,
        )
        assert profile.is_complete() is False

    def test_is_complete_with_missing_calories(self):
        """Profile is incomplete when calories missing."""
        profile = NutrientProfile(
            carbs_g=10.0,
            protein_g=3.0,
            fat_g=1.0,
            calories_kcal=None,
        )
        assert profile.is_complete() is False

    def test_has_minimal_data_true(self):
        """Profile has minimal data when carbs and calories present."""
        profile = NutrientProfile(
            carbs_g=10.0,
            calories_kcal=100.0,
            fiber_g=None,
            protein_g=None,
        )
        assert profile.has_minimal_data() is True

    def test_has_minimal_data_false_no_carbs(self):
        """Profile lacks minimal data when carbs missing."""
        profile = NutrientProfile(
            carbs_g=None,
            calories_kcal=100.0,
        )
        assert profile.has_minimal_data() is False

    def test_has_minimal_data_false_no_calories(self):
        """Profile lacks minimal data when calories missing."""
        profile = NutrientProfile(
            carbs_g=10.0,
            calories_kcal=None,
        )
        assert profile.has_minimal_data() is False


class TestExtractNutrientsOff:
    """Tests for extract_nutrients_off function."""

    def test_extract_complete_product(self):
        """Extract all nutrients from a fully populated product."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Test Food",
            carbs_100g=15.0,
            fiber_100g=3.0,
            sugars_100g=5.0,
            proteins_100g=4.0,
            fat_100g=2.0,
            energy_kcal_100g=120.0,
            serving_quantity=50.0,
        )
        
        result = extract_nutrients_off(product)
        
        assert result.carbs_g == 15.0
        assert result.fiber_g == 3.0
        assert result.sugars_g == 5.0
        assert result.protein_g == 4.0
        assert result.fat_g == 2.0
        assert result.calories_kcal == 120.0
        assert result.serving_weight_g == 50.0

    def test_extract_partial_product(self):
        """Extract nutrients from a product with missing fields."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Test Food",
            carbs_100g=10.0,
            fiber_100g=None,
            sugars_100g=None,
            proteins_100g=2.0,
            fat_100g=None,
            energy_kcal_100g=80.0,
        )
        
        result = extract_nutrients_off(product)
        
        assert result.carbs_g == 10.0
        assert result.fiber_g is None
        assert result.sugars_g is None
        assert result.protein_g == 2.0
        assert result.fat_g is None
        assert result.calories_kcal == 80.0

    def test_extract_empty_product(self):
        """Extract from product with no nutrition data."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Empty Product",
        )
        
        result = extract_nutrients_off(product)
        
        assert result.carbs_g is None
        assert result.fiber_g is None
        assert result.sugars_g is None
        assert result.protein_g is None
        assert result.fat_g is None
        assert result.calories_kcal is None
        assert result.serving_weight_g is None


class TestExtractNutrientsSafe:
    """Tests for extract_nutrients_safe function."""

    def test_extract_safe_uses_defaults(self):
        """Safe extraction uses 0.0 for missing numeric fields."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Incomplete Product",
            carbs_100g=5.0,
            energy_kcal_100g=40.0,
        )
        
        result = extract_nutrients_safe(product)
        
        assert result.carbs_g == 5.0
        assert result.calories_kcal == 40.0
        assert result.fiber_g == 0.0  # Default
        assert result.sugars_g == 0.0  # Default
        assert result.protein_g == 0.0  # Default
        assert result.fat_g == 0.0  # Default


class TestOFFExamples:
    """Tests using real-world-like OFF product examples."""

    def test_big_mac_example(self):
        """Extract nutrients from Big Mac-style product."""
        product = OpenFoodFactsProduct(
            code="0544310000000",
            product_name="Big Mac",
            carbs_100g=15.4,
            fiber_100g=1.7,
            sugars_100g=5.0,
            proteins_100g=12.2,
            fat_100g=11.2,
            energy_kcal_100g=256.0,
            serving_quantity=100.0,
        )
        
        result = extract_nutrients_off(product)
        
        assert result.carbs_g == 15.4
        assert result.protein_g == 12.2
        assert result.fat_g == 11.2
        assert result.calories_kcal == 256.0

    def test_generic_bread_example(self):
        """Extract nutrients from generic bread product."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Whole Wheat Bread",
            carbs_100g=49.0,
            fiber_100g=6.0,
            sugars_100g=3.0,
            proteins_100g=8.0,
            fat_100g=2.0,
            energy_kcal_100g=247.0,
            serving_quantity=35.0,
        )
        
        result = extract_nutrients_off(product)
        
        assert result.carbs_g == 49.0
        assert result.fiber_g == 6.0
        assert result.protein_g == 8.0
        assert result.fat_g == 2.0
        assert result.calories_kcal == 247.0
        assert result.serving_weight_g == 35.0