"""Meal composition service for aggregating nutrients from multiple foods.

Computes total nutrients for a meal from multiple foods with appropriate
weighting and provenance handling.
"""

from dataclasses import dataclass
from typing import Optional, List

from app.food.nutrient_extractor import NutrientProfile, extract_nutrients_off
from app.food.provenance import FoodProvenance, SourceTrustTier, compute_provenance
from app.food.serving_normalizer import normalize_from_off
from app.food.models import OpenFoodFactsProduct


@dataclass
class MealItem:
    """A single food item in a meal."""
    food: OpenFoodFactsProduct
    quantity: float
    unit: str


@dataclass
class MealComposition:
    """Result of composing a meal from multiple food items."""
    total_nutrients: NutrientProfile
    provenance: FoodProvenance
    item_count: int
    
    def is_reliable(self) -> bool:
        """Return True if meal composition is reliable."""
        return self.provenance.is_reliable() and self.total_nutrients.has_minimal_data()


def compose_meal(items: List[MealItem]) -> MealComposition:
    """Compose a meal from multiple food items.
    
    Args:
        items: List of MealItem objects with food, quantity, and unit
        
    Returns:
        MealComposition with total nutrients and aggregated provenance
    """
    total_carbs = 0.0
    total_fiber = 0.0
    total_sugars = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_calories = 0.0
    total_grams = 0.0
    
    worst_provenance: Optional[FoodProvenance] = None
    worst_confidence = 1.0
    
    for item in items:
        # Normalize quantity to grams
        normalized = normalize_from_off(item.food, item.quantity, item.unit)
        grams = normalized.quantity_g
        total_grams += grams
        
        # Extract nutrients per 100g
        nutrients = extract_nutrients_off(item.food)
        
        # Scale nutrients by actual quantity (OFF data is per 100g)
        factor = grams / 100.0
        
        if nutrients.carbs_g is not None:
            total_carbs += nutrients.carbs_g * factor
        if nutrients.fiber_g is not None:
            total_fiber += nutrients.fiber_g * factor
        if nutrients.sugars_g is not None:
            total_sugars += nutrients.sugars_g * factor
        if nutrients.protein_g is not None:
            total_protein += nutrients.protein_g * factor
        if nutrients.fat_g is not None:
            total_fat += nutrients.fat_g * factor
        if nutrients.calories_kcal is not None:
            total_calories += nutrients.calories_kcal * factor
        
        # Track worst provenance
        prov = compute_provenance(
            source="openfoodfacts",
            barcode=item.food.code,
            query_barcode=item.food.code,
            serving_weight=item.food.serving_quantity,
        )
        conf = prov.confidence_score()
        if conf < worst_confidence:
            worst_confidence = conf
            worst_provenance = prov
    
    total_nutrients = NutrientProfile(
        carbs_g=round(total_carbs, 2) if total_carbs > 0 else None,
        fiber_g=round(total_fiber, 2) if total_fiber > 0 else None,
        sugars_g=round(total_sugars, 2) if total_sugars > 0 else None,
        protein_g=round(total_protein, 2) if total_protein > 0 else None,
        fat_g=round(total_fat, 2) if total_fat > 0 else None,
        calories_kcal=round(total_calories, 2) if total_calories > 0 else None,
        serving_weight_g=round(total_grams, 2),
    )
    
    # Use worst provenance or default if no items
    if worst_provenance is None:
        provenance = FoodProvenance(
            source_name="empty",
            serving_certainty=0.0,
            source_trust_tier=SourceTrustTier.ESTIMATED,
        )
    else:
        provenance = worst_provenance
    
    return MealComposition(
        total_nutrients=total_nutrients,
        provenance=provenance,
        item_count=len(items),
    )