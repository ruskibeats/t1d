#!/usr/bin/env python3
"""
Generate 90-day food history for all sim users.

Creates synthetic but clinically-plausible food/insulin/CGM data
for 12 anchor archetypes.
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np

from app.simulator.anchors import ANCHOR_PARAMETER_RANGES, AnchorType
from app.simulator.schemas import AnchorParameterRange

OUTPUT_FILE = Path("data/food_history_90d.json")

# Common foods database (carb estimates in grams)
FOODS_DB = {
    "pizza_pepperoni_large": {"name": "Pepperoni Pizza (Large)", "carbs_per_serving": 180, "fat_g": 70},
    "beer_lager": {"name": "Lager Beer", "carbs_per_serving": 11, "fat_g": 0},
    "sandwich_turkey": {"name": "Turkey Sandwich", "carbs_per_serving": 45, "fat_g": 12},
    "pasta_cream": {"name": "Pasta Alfredo", "carbs_per_serving": 60, "fat_g": 25},
    "salad_caesar": {"name": "Caesar Salad", "carbs_per_serving": 15, "fat_g": 20},
    "sushi_combo": {"name": "Sushi Combo", "carbs_per_serving": 55, "fat_g": 15},
    "curry_chicken": {"name": "Chicken Curry", "carbs_per_serving": 40, "fat_g": 20},
    "smoothie_berry": {"name": "Berry Smoothie", "carbs_per_serving": 45, "fat_g": 5},
    "burrito_beef": {"name": "Beef Burrito", "carbs_per_serving": 65, "fat_g": 25},
    "oatmeal_raisin": {"name": "Oatmeal with Raisins", "carbs_per_serving": 50, "fat_g": 8},
    "chinese_lo_mein": {"name": "Lo Mein Noodles", "carbs_per_serving": 75, "fat_g": 15},
    "steak_baked_potato": {"name": "Steak with Baked Potato", "carbs_per_serving": 45, "fat_g": 35},
}

def generate_food_entries_for_anchor(anchor: AnchorType, days: int = 90) -> list:
    """Generate synthetic food history for one anchor type."""
    anchor_params = ANCHOR_PARAMETER_RANGES[anchor]
    entries = []
    
    start_date = datetime(2025, 4, 1, 0, 0)  # Fixed start date
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        
        # Generate 2-4 meals per day
        n_meals = random.randint(2, 4)
        meal_times = sorted([random.randint(360, 1200) for _ in range(n_meals)])  # minutes from midnight
        
        for meal_time in meal_times:
            meal_dt = current_date + timedelta(minutes=meal_time)
            
            # Select random food
            food_key = random.choice(list(FOODS_DB.keys()))
            food = FOODS_DB[food_key]
            
            # Add carb estimation error (±15%)
            carb_error = random.gauss(1.0, 0.15)
            carbs = int(food["carbs_per_serving"] * carb_error)
            
            # Calculate bolus based on anchor's carb ratio
            carb_ratio_range = anchor_params.carb_ratio
            cr = random.uniform(*carb_ratio_range)
            bolus = round(carbs / cr, 1)
            
            # Pre-bolus timing (15-30 min for well_controlled, variable for others)
            if anchor == AnchorType.WELL_CONTROLLED:
                prebolus_mins = random.randint(15, 30)
            else:
                prebolus_mins = random.randint(0, 45)  # Variable timing
            
            entries.append({
                "timestamp": meal_dt.isoformat(),
                "anchor_type": anchor.value,
                "food": food["name"],
                "carb_estimate_g": carbs,
                "fat_g": food["fat_g"],
                "bolus_units": bolus,
                "prebolus_minutes": prebolus_mins,
                "carb_ratio_used": round(cr, 1),
            })
    
    return entries

def generate_cgm_impacts(entries: list, anchor: AnchorType) -> list:
    """Add synthetic CGM impacts for each food entry."""
    anchor_params = ANCHOR_PARAMETER_RANGES[anchor]
    impacts = []
    
    for entry in entries:
        # Generate CGM response parameters
        fat_delay_range = anchor_params.fat_delay_hours
        fat_delay_mean = (fat_delay_range[0] + fat_delay_range[1]) / 2
        fat_delay_sd = (fat_delay_range[1] - fat_delay_range[0]) / 4
        
        impact = {
            **entry,
            "cgm_impact": {
                "expected_peak_delta": round(random.uniform(30, 100), 1),
                "peak_time_minutes": random.randint(60, 180),
                "fat_delay_hours": round(max(0, random.gauss(fat_delay_mean, fat_delay_sd)), 1),
                "exercise_modifier": random.choice([0.8, 0.9, 1.0, 1.1, 1.2]),  # Random exercise effects
            }
        }
        impacts.append(impact)
    
    return impacts

if __name__ == "__main__":
    all_entries = []
    
    print("Generating 90-day food history for 12 anchor types...")
    
    for anchor in AnchorType:
        print(f"  Generating for {anchor.value}...")
        entries = generate_food_entries_for_anchor(anchor)
        entries_with_impacts = generate_cgm_impacts(entries, anchor)
        all_entries.extend(entries_with_impacts)
        print(f"    Generated {len(entries)} entries")
    
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_entries, f, indent=2)
    
    print(f"\nTotal entries: {len(all_entries)}")
    print(f"Saved to: {OUTPUT_FILE}")