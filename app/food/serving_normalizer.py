"""Serving normalization helper for converting food quantities to canonical units.

Normalizes food quantities into a canonical gram-based or equivalent representation
so nutrient aggregation is correct across different serving formats.
"""

from dataclasses import dataclass
from typing import Optional, Tuple

from app.food.models import OpenFoodFactsProduct


@dataclass
class NormalizedQuantity:
    """Normalized food quantity with confidence tracking."""
    
    quantity_g: float
    confidence: float  # 0.0 to 1.0
    notes: Optional[str] = None
    
    def __post_init__(self):
        if self.confidence < 0.0:
            self.confidence = 0.0
        if self.confidence > 1.0:
            self.confidence = 1.0


# Standard serving weight defaults for common units (in grams)
DEFAULT_SERVING_WEIGHTS = {
    # Volume to weight (approximate, varies by density)
    "ml": 1.0,  # 1ml water ≈ 1g
    "l": 1000.0,
    "tsp": 5.0,
    "tbsp": 15.0,
    "cup": 240.0,
    "fl oz": 30.0,
    # Countable items
    "slice": 30.0,  # Average bread slice
    "piece": 50.0,  # Generic piece weight
    "serving": 100.0,  # Default serving
    "unit": 100.0,
    "g": 1.0,
    "kg": 1000.0,
}


def normalize_quantity(
    quantity: float,
    unit: str,
    product: Optional[OpenFoodFactsProduct] = None,
) -> NormalizedQuantity:
    """Convert a food quantity to canonical grams.
    
    Args:
        quantity: The amount of the food item
        unit: Unit string (g, kg, ml, l, slice, piece, serving, cup, etc.)
        product: Optional OpenFoodFacts product for serving weight lookup
        
    Returns:
        NormalizedQuantity with grams and confidence level
    """
    unit_lower = unit.lower().strip()
    
    # Direct gram units
    if unit_lower in ("g", "gram", "grams"):
        return NormalizedQuantity(quantity_g=quantity, confidence=1.0)
    
    if unit_lower in ("kg", "kilogram", "kilograms"):
        return NormalizedQuantity(quantity_g=quantity * 1000, confidence=1.0)
    
    # Use product serving quantity if available
    if product and product.serving_quantity:
        if unit_lower in ("serving", "servings", "unit"):
            return NormalizedQuantity(
                quantity_g=quantity * product.serving_quantity,
                confidence=0.9,
                notes="Using product serving_quantity"
            )
    
    # Check for explicit serving size in product
    if product and product.serving_size:
        # Parse serving_size text like "30 g" or "1 slice"
        pass
    
    # Fallback to standard weights
    if unit_lower in DEFAULT_SERVING_WEIGHTS:
        weight = DEFAULT_SERVING_WEIGHTS[unit_lower]
        confidence = 0.7 if unit_lower in ("slice", "piece", "serving") else 0.8
        return NormalizedQuantity(
            quantity_g=quantity * weight,
            confidence=confidence,
            notes=f"Using default weight for {unit}"
        )
    
    # Unknown unit - return with warning
    return NormalizedQuantity(
        quantity_g=quantity * 100,  # Assume 100g default
        confidence=0.3,
        notes=f"Unknown unit '{unit}', assumed 100g per unit"
    )


def normalize_from_off(product: OpenFoodFactsProduct, quantity: float, unit: str) -> NormalizedQuantity:
    """Normalize quantity specifically for an OpenFoodFacts product.
    
    This version prefers using the product's own serving data when available.
    
    Args:
        product: OpenFoodFactsProduct model instance
        quantity: The amount
        unit: Unit string
        
    Returns:
        NormalizedQuantity with grams and confidence
    """
    unit_lower = unit.lower().strip()
    
    # Check for explicit serving_size field (text like "30 g" or "1 slice")
    if product.serving_size and unit_lower in ("serving", "servings", ""):
        # Could parse this more intelligently
        pass
    
    # Use serving_quantity when available
    if product.serving_quantity:
        if unit_lower in ("slice", "slices"):
            # Check if product name suggests bread/slice
            name = (product.product_name or "").lower()
            if "bread" in name or "roll" in name:
                return NormalizedQuantity(
                    quantity_g=quantity * product.serving_quantity,
                    confidence=0.95,
                    notes="Bread slice from product serving_quantity"
                )
            return NormalizedQuantity(
                quantity_g=quantity * product.serving_quantity,
                confidence=0.9,
                notes="Using product serving_quantity"
            )
        if unit_lower in ("piece", "pieces", "unit", "units"):
            return NormalizedQuantity(
                quantity_g=quantity * product.serving_quantity,
                confidence=0.9,
                notes="Using product serving_quantity"
            )
    
    # Fall back to standard normalization
    return normalize_quantity(quantity, unit, product)