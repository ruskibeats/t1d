"""Tests for meal composition service."""

import pytest

from app.food.meal_composition import MealItem, MealComposition, compose_meal
from app.food.models import OpenFoodFactsProduct
from app.food.provenance import SourceTrustTier


class TestMealComposition:
    """Tests for meal composition service."""

    def test_single_item_meal(self):
        """Compose a meal with a single food item."""
        product = OpenFoodFactsProduct(
            code="1234567890123",
            product_name="Test Cookie",
            carbs_100g=20.0,
            proteins_100g=3.0,
            fat_100g=10.0,
            energy_kcal_100g=200.0,
            serving_quantity=10.0,
        )
        
        meal = compose_meal([MealItem(food=product, quantity=2, unit="piece")])
        
        # 2 pieces at 10g each = 20g total, scaled from 100g basis
        # 20g / 100g * 20g carbs = 4g carbs
        assert meal.total_nutrients.carbs_g == 4.0
        assert meal.total_nutrients.protein_g == 0.6  # 20g * 3g / 100g
        assert meal.total_nutrients.fat_g == 2.0  # 20g * 10g / 100g
        assert meal.total_nutrients.calories_kcal == 40.0  # 20g * 200kcal / 100g

    def test_multi_item_meal(self):
        """Compose a meal with multiple food items."""
        product1 = OpenFoodFactsProduct(
            code="111",
            product_name="Bread",
            carbs_100g=49.0,
            proteins_100g=8.0,
            serving_quantity=35.0,
        )
        product2 = OpenFoodFactsProduct(
            code="222",
            product_name="Peanut Butter",
            carbs_100g=20.0,
            proteins_100g=25.0,
            serving_quantity=16.0,
        )
        
        meal = compose_meal([
            MealItem(food=product1, quantity=2, unit="slice"),
            MealItem(food=product2, quantity=1, unit="tbsp"),
        ])
        
        # 2 slices at 35g = 70g, scaled
        assert meal.total_nutrients.carbs_g is not None
        assert meal.total_nutrients.protein_g is not None
        assert meal.item_count == 2

    def test_empty_meal(self):
        """Empty meal produces zero nutrients."""
        meal = compose_meal([])
        
        assert meal.total_nutrients.carbs_g is None
        assert meal.total_nutrients.calories_kcal is None
        assert meal.item_count == 0

    def test_is_reliable_with_good_data(self):
        """Meal with good data is reliable."""
        product = OpenFoodFactsProduct(
            code="123",
            product_name="Good Food",
            carbs_100g=10.0,
            proteins_100g=5.0,
            fat_100g=2.0,
            energy_kcal_100g=100.0,
            serving_quantity=50.0,
        )
        
        meal = compose_meal([MealItem(food=product, quantity=1, unit="g")])
        
        assert meal.is_reliable() is True

    def test_provenance_aggregation(self):
        """Provenance reflects worst item quality."""
        product = OpenFoodFactsProduct(
            code="123",
            product_name="Food",
            carbs_100g=10.0,
            proteins_100g=5.0,
            energy_kcal_100g=100.0,
            serving_quantity=50.0,
        )
        
        meal = compose_meal([MealItem(food=product, quantity=1, unit="g")])
        
        assert meal.provenance.source_trust_tier == SourceTrustTier.OFFICIAL
        assert meal.provenance.barcode_match is True


class TestRealWorldScenarios:
    """Tests for real-world meal scenarios."""

    def test_sandwich_meal(self):
        """A sandwich with bread and peanut butter."""
        bread = OpenFoodFactsProduct(
            code="0544310000000",
            product_name="Bread",
            carbs_100g=49.0,
            proteins_100g=8.0,
            fat_100g=2.0,
            energy_kcal_100g=247.0,
            serving_quantity=35.0,
        )
        peanut_butter = OpenFoodFactsProduct(
            code="0004900002123",
            product_name="Peanut Butter",
            carbs_100g=20.0,
            proteins_100g=25.0,
            fat_100g=50.0,
            energy_kcal_100g=588.0,
            serving_quantity=16.0,
        )
        
        meal = compose_meal([
            MealItem(food=bread, quantity=2, unit="slice"),
            MealItem(food=peanut_butter, quantity=1, unit="tbsp"),
        ])
        
        # Should have reasonable totals
        assert meal.total_nutrients.carbs_g is not None
        assert meal.total_nutrients.calories_kcal > 200
        assert meal.item_count == 2