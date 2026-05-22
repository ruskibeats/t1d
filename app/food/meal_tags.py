"""Meal classification tags for deterministic meal interpretation.

Provides threshold-based tags that help the forecast engine and UI interpret
a meal beyond raw nutrient totals.
"""

from dataclasses import dataclass
from typing import List

from app.food.nutrient_extractor import NutrientProfile


# Threshold configuration for meal tags (per 100g meal)
TAG_THRESHOLDS = {
    # Carb thresholds (g per 100g)
    "low_carb": 10,
    "moderate_carb": 25,
    "high_carb": 40,
    
    # Protein thresholds (g per 100g)
    "high_protein": 20,
    
    # Fat thresholds (g per 100g)
    "high_fat": 20,
    
    # Meal size threshold (kcal per 100g)
    "light_snack": 150,
}


@dataclass
class MealTags:
    """Classification tags for a meal."""
    tags: List[str]
    
    def has_tag(self, tag: str) -> bool:
        """Check if a specific tag is present."""
        return tag in self.tags
    
    def __contains__(self, tag: str) -> bool:
        return self.has_tag(tag)


def generate_meal_tags(nutrients: NutrientProfile) -> MealTags:
    """Generate classification tags for a meal based on nutrient totals.
    
    Tags are generated deterministically from thresholds applied to the
    nutrient profile. Tags are per 100g basis for comparability.
    
    Args:
        nutrients: NutrientProfile with carb, protein, fat, calories per 100g
        
    Returns:
        MealTags object with applicable tag strings
    """
    tags = []
    
    # Get values with defaults
    carbs = nutrients.carbs_g or 0
    protein = nutrients.protein_g or 0
    fat = nutrients.fat_g or 0
    calories = nutrients.calories_kcal or 0
    
    # Carb classification
    if carbs <= TAG_THRESHOLDS["low_carb"]:
        tags.append("low-carb")
    elif carbs <= TAG_THRESHOLDS["moderate_carb"]:
        tags.append("moderate-carb")
    elif carbs <= TAG_THRESHOLDS["high_carb"]:
        tags.append("high-carb")
    else:
        tags.append("very-high-carb")
    
    # Protein classification
    if protein >= TAG_THRESHOLDS["high_protein"]:
        tags.append("high-protein")
    
    # Fat classification
    if fat >= TAG_THRESHOLDS["high_fat"]:
        tags.append("high-fat")
    
    # Meal size classification
    if calories <= TAG_THRESHOLDS["light_snack"]:
        tags.append("light-snack")
    
    # Mixed meal detection (all macros present in moderate amounts)
    if carbs > 5 and carbs < 30 and protein > 5 and fat > 5:
        tags.append("mixed-meal")
    
    return MealTags(tags=tags)


def get_carb_load_class(carbs_g: float) -> str:
    """Get carb load classification from total carbs.
    
    Args:
        carbs_g: Total carbohydrates in grams
        
    Returns:
        Carb load class string: "light", "moderate", "heavy"
    """
    if carbs_g < 15:
        return "light"
    elif carbs_g < 45:
        return "moderate"
    else:
        return "heavy"


def get_meal_complexity(tags: MealTags) -> str:
    """Determine meal complexity from tags.
    
    Args:
        tags: MealTags object
        
    Returns:
        Complexity string: "simple", "moderate", "complex"
    """
    tag_count = len(tags.tags)
    
    if tag_count <= 2:
        return "simple"
    elif tag_count <= 4:
        return "moderate"
    else:
        return "complex"