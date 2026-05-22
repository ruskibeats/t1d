"""Nutrient extraction helper from OpenFoodFacts products.

Extracts canonical nutrient values from OpenFoodFactsProduct rows into a stable
internal format suitable for meal composition and forecasting.

This module abstracts the raw OpenFoodFacts column structure behind a clean
interface with explicit missing data handling.
"""

from dataclasses import dataclass
from typing import Optional

from app.food.models import OpenFoodFactsProduct


@dataclass
class NutrientProfile:
    """Canonical nutrient values per 100g extracted from a food item."""
    
    carbs_g: Optional[float] = None
    fiber_g: Optional[float] = None
    sugars_g: Optional[float] = None
    protein_g: Optional[float] = None
    fat_g: Optional[float] = None
    calories_kcal: Optional[float] = None
    serving_weight_g: Optional[float] = None
    
    def is_complete(self) -> bool:
        """Return True if all critical nutrients are present."""
        return all([
            self.carbs_g is not None,
            self.protein_g is not None,
            self.fat_g is not None,
            self.calories_kcal is not None,
        ])
    
    def has_minimal_data(self) -> bool:
        """Return True if at least carbs and calories are present."""
        return self.carbs_g is not None and self.calories_kcal is not None


def extract_nutrients_off(product: OpenFoodFactsProduct) -> NutrientProfile:
    """Extract canonical nutrients from an OpenFoodFactsProduct row.
    
    Maps OFF columns to canonical nutrient fields with explicit null handling.
    The OFF data is per 100g basis; serving_weight_g is extracted separately.
    
    Args:
        product: OpenFoodFactsProduct SQLAlchemy model instance
        
    Returns:
        NutrientProfile with extracted values (None for missing fields)
    """
    return NutrientProfile(
        carbs_g=product.carbs_100g,
        fiber_g=product.fiber_100g,
        sugars_g=product.sugars_100g,
        protein_g=product.proteins_100g,
        fat_g=product.fat_100g,
        calories_kcal=product.energy_kcal_100g,
        serving_weight_g=product.serving_quantity,
    )


def extract_nutrients_safe(product: OpenFoodFactsProduct) -> NutrientProfile:
    """Extract nutrients with defensive defaults for missing data.
    
    Uses 0.0 for known-zero fields when OFF data is missing,
    suitable for aggregation paths that can't handle None.
    
    Args:
        product: OpenFoodFactsProduct SQLAlchemy model instance
        
    Returns:
        NutrientProfile with 0.0 defaults for missing numeric fields
    """
    return NutrientProfile(
        carbs_g=product.carbs_100g if product.carbs_100g is not None else 0.0,
        fiber_g=product.fiber_100g if product.fiber_100g is not None else 0.0,
        sugars_g=product.sugars_100g if product.sugars_100g is not None else 0.0,
        protein_g=product.proteins_100g if product.proteins_100g is not None else 0.0,
        fat_g=product.fat_100g if product.fat_100g is not None else 0.0,
        calories_kcal=product.energy_kcal_100g if product.energy_kcal_100g is not None else 0.0,
        serving_weight_g=product.serving_quantity,
    )