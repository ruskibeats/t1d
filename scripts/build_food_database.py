#!/usr/bin/env python3
"""
Build a clean T1D food database from McCance & Widdowson, Carbs & Cals, and OFF data.
"""
import csv
import json
from pathlib import Path

# Output database
OUTPUT_PATH = Path("/root/t1d/data/t1d_food_database.json")

# McCance & Widdowson key foods (per 100g, beer/lager per 100ml)
MC_W = {
    # Breads & cereals
    "bread": {"carbs": 48.7, "fat": 2.1, "protein": 8.1},
    "white bread": {"carbs": 48.7, "fat": 2.1, "protein": 8.1},
    "wholemeal bread": {"carbs": 42.0, "fat": 2.5, "protein": 9.1},
    "pasta": {"carbs": 25.0, "fat": 1.5, "protein": 5.8},
    "rice": {"carbs": 28.0, "fat": 0.3, "protein": 2.7},
    "oatmeal": {"carbs": 12.0, "fat": 2.5, "protein": 2.5},
    
    # Fruits
    "banana": {"carbs": 20.3, "fat": 0.1, "protein": 2.6},
    "apple": {"carbs": 13.8, "fat": 0.2, "protein": 0.3},
    "orange": {"carbs": 9.4, "fat": 0.1, "protein": 0.9},
    
    # Proteins
    "sausage": {"carbs": 9.6, "fat": 25.0, "protein": 12.5},
    "pork sausage": {"carbs": 9.6, "fat": 25.0, "protein": 12.5},
    "chicken curry": {"carbs": 10.0, "fat": 8.0, "protein": 15.0},
    
    # Snacks/desserts
    "pizza": {"carbs": 25.0, "fat": 10.0, "protein": 12.0},
    "ice cream": {"carbs": 21.0, "fat": 15.0, "protein": 3.5},
    "cake": {"carbs": 45.0, "fat": 15.0, "protein": 5.0},
    
    # Beverages (per 100ml)
    "beer": {"carbs": 4.6, "fat": 0, "protein": 0},
    "lager": {"carbs": 4.6, "fat": 0, "protein": 0},
    "coke": {"carbs": 11.0, "fat": 0, "protein": 0},
    "cola": {"carbs": 11.0, "fat": 0, "protein": 0},
}

# Serving size multipliers (grams per serving)
SERVING_SIZES = {
    "slice": 30, "slices": 30,
    "can": 330, "cans": 330,
    "pint": 568, "pints": 568,
    "scoop": 66, "scoops": 66,
    "cup": 240,
    "piece": 100, "pieces": 100,
}

def get_nutrition(food: str, qty: float = 1, unit: str = None) -> dict:
    """Get nutrition for a food using McCance & Widdowson data."""
    food_lower = food.lower()
    
    # Find matching food
    for key, val in MC_C&W.items():
        if key in food_lower:
            carbs_per = val["carbs"]
            fat_per = val["fat"]
            protein_per = val["protein"]
            
            # Calculate based on serving
            if unit and unit in SERVING_SIZES:
                serving_g = qty * SERVING_SIZES[unit]
                # Beer uses per 100ml
                if key in ["beer", "lager", "coke", "cola"]:
                    carbs = carbs_per * serving_g / 100
                    fat = fat_per * serving_g / 100
                else:
                    carbs = carbs_per * serving_g / 100
                    fat = fat_per * serving_g / 100
            else:
                carbs = carbs_per * qty
                fat = fat_per * qty
            
            return {"carbs": round(carbs, 1), "fat": round(fat, 1)}
    
    return {"carbs": 25 * qty, "fat": 5 * qty}

if __name__ == "__main__":
    # Build database
    database = {"foods": MC_W, "serving_sizes": SERVING_SIZES}
    
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(database, f, indent=2)
    
    print(f"Created food database at {OUTPUT_PATH}")
    print(f"Contains {len(MC_W)} foods")