"""Tests for meal classification tags."""

import pytest

from app.food.meal_tags import (
    MealTags,
    generate_meal_tags,
    get_carb_load_class,
    get_meal_complexity,
    TAG_THRESHOLDS,
)
from app.food.nutrient_extractor import NutrientProfile


class TestMealTags:
    """Tests for MealTags dataclass."""

    def test_has_tag_present(self):
        """Tag presence check works correctly."""
        tags = MealTags(tags=["low-carb", "high-protein"])
        assert tags.has_tag("low-carb") is True
        assert tags.has_tag("high-protein") is True

    def test_has_tag_absent(self):
        """Absent tag returns False."""
        tags = MealTags(tags=["low-carb"])
        assert tags.has_tag("high-fat") is False

    def test_contains_operator(self):
        """Contains operator works for tags."""
        tags = MealTags(tags=["mixed-meal"])
        assert "mixed-meal" in tags
        assert "low-carb" not in tags


class TestGenerateMealTags:
    """Tests for generate_meal_tags function."""

    def test_low_carb_tag(self):
        """Low carb tag for minimal carbs."""
        nutrients = NutrientProfile(carbs_g=5, protein_g=10, fat_g=5)
        tags = generate_meal_tags(nutrients)
        assert "low-carb" in tags.tags

    def test_moderate_carb_tag(self):
        """Moderate carb tag for medium carbs."""
        nutrients = NutrientProfile(carbs_g=20, protein_g=10, fat_g=5)
        tags = generate_meal_tags(nutrients)
        assert "moderate-carb" in tags.tags

    def test_high_carb_tag(self):
        """High carb tag for high carbs."""
        nutrients = NutrientProfile(carbs_g=35, protein_g=10, fat_g=5)
        tags = generate_meal_tags(nutrients)
        assert "high-carb" in tags.tags

    def test_very_high_carb_tag(self):
        """Very high carb tag for excessive carbs."""
        nutrients = NutrientProfile(carbs_g=50, protein_g=10, fat_g=5)
        tags = generate_meal_tags(nutrients)
        assert "very-high-carb" in tags.tags

    def test_high_protein_tag(self):
        """High protein tag when protein exceeds threshold."""
        nutrients = NutrientProfile(carbs_g=10, protein_g=25, fat_g=5)
        tags = generate_meal_tags(nutrients)
        assert "high-protein" in tags.tags

    def test_high_fat_tag(self):
        """High fat tag when fat exceeds threshold."""
        nutrients = NutrientProfile(carbs_g=10, protein_g=10, fat_g=25)
        tags = generate_meal_tags(nutrients)
        assert "high-fat" in tags.tags

    def test_light_snack_tag(self):
        """Light snack tag for low-calorie meals."""
        nutrients = NutrientProfile(carbs_g=5, protein_g=3, fat_g=2, calories_kcal=100)
        tags = generate_meal_tags(nutrients)
        assert "light-snack" in tags.tags

    def test_mixed_meal_tag(self):
        """Mixed meal tag when all macros are present in moderate amounts."""
        nutrients = NutrientProfile(carbs_g=15, protein_g=10, fat_g=10)
        tags = generate_meal_tags(nutrients)
        assert "mixed-meal" in tags.tags

    def test_multiple_tags(self):
        """Multiple tags can be generated for same meal."""
        nutrients = NutrientProfile(carbs_g=50, protein_g=30, fat_g=30, calories_kcal=500)
        tags = generate_meal_tags(nutrients)
        assert len(tags.tags) >= 3


class TestCarbLoadClass:
    """Tests for carb load classification."""

    def test_light_carb_load(self):
        """Light carb load for low carbs."""
        assert get_carb_load_class(10) == "light"
        assert get_carb_load_class(0) == "light"

    def test_moderate_carb_load(self):
        """Moderate carb load for medium carbs."""
        assert get_carb_load_class(20) == "moderate"
        assert get_carb_load_class(44) == "moderate"

    def test_heavy_carb_load(self):
        """Heavy carb load for high carbs."""
        assert get_carb_load_class(50) == "heavy"
        assert get_carb_load_class(100) == "heavy"


class TestMealComplexity:
    """Tests for meal complexity classification."""

    def test_simple_complexity(self):
        """Simple meals have few tags."""
        tags = MealTags(tags=["low-carb"])
        assert get_meal_complexity(tags) == "simple"

    def test_moderate_complexity(self):
        """Moderate complexity for medium tag count."""
        tags = MealTags(tags=["low-carb", "high-protein", "light-snack"])
        assert get_meal_complexity(tags) == "moderate"

    def test_complex_complexity(self):
        """Complex meals have many tags."""
        tags = MealTags(tags=["high-carb", "high-protein", "high-fat", "light-snack", "mixed-meal"])
        assert get_meal_complexity(tags) == "complex"


class TestRealWorldScenarios:
    """Tests for real-world meal scenarios."""

    def test_eggs_bread_scenario(self):
        """Eggs + bread should produce expected tags."""
        # Approximate: 2 eggs (10g carbs) + 2 bread slices (50g carbs)
        nutrients = NutrientProfile(
            carbs_g=30,  # Combined: high-carb (>=25 and <=40)
            protein_g=25,  # High protein from eggs (exceeds 20g threshold)
            fat_g=12,  # Moderate fat
            calories_kcal=350,
        )
        tags = generate_meal_tags(nutrients)
        
        assert "high-carb" in tags.tags
        assert "high-protein" in tags.tags

    def test_salad_scenario(self):
        """Healthy salad should be light, low-carb."""
        nutrients = NutrientProfile(
            carbs_g=8,
            protein_g=5,
            fat_g=25,  # High fat to trigger high-fat tag
            calories_kcal=180,
        )
        tags = generate_meal_tags(nutrients)
        
        assert "low-carb" in tags.tags
        assert "high-fat" in tags.tags

    def test_pasta_scenario(self):
        """Pasta dinner should be high-carb."""
        nutrients = NutrientProfile(
            carbs_g=60,
            protein_g=15,
            fat_g=8,
            calories_kcal=500,
        )
        tags = generate_meal_tags(nutrients)
        
        assert "very-high-carb" in tags.tags