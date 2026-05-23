#!/usr/bin/env python3
"""
Natural Language Simulator Interaction Demo

Shows how the simulator responds to natural language questions about food.
"""

import json
from pathlib import Path
from app.simulator.schemas import AnchorType
from app.simulator.patient_factory import generate_patient_config, generate_profile_json

# Create patient profile
patient_config = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42)
profile = generate_profile_json(patient_config)

# Load food history for context
history_path = Path("/root/t1d/data/food_history_90d.json")
history = json.loads(history_path.read_text()) if history_path.exists() else []

# Find similar meals in history
def find_similar_meals(query: str, limit=3):
    query_lower = query.lower()
    matches = []
    for entry in history[:1000]:  # Check first 1000 entries
        food = entry.get('food_type', '').lower()
        if any(word in food for word in query_lower.split()):
            matches.append(entry)
            if len(matches) >= limit:
                break
    return matches

print("=" * 65)
print("🤖 T1D COMPANION SIMULATOR - Natural Language Mode")
print("=" * 65)
print(f"\n👤 Patient: {profile['anchor_label']}")
print(f"   TIR: ~{profile['estimated_tir']}%, Hypo freq: {profile['estimated_hypo_frequency']}")
print(f"   Carb ratio: 1U/{patient_config.carb_ratio:.1f}g, Sensitivity: {patient_config.insulin_sensitivity:.0f} mg/dL/U\n")

# User's question
user_query = "I am on holiday in italy, it is 32 degrees outside and I am walking around sightseeing all day, I want to eat some pizza, drink some beers and have ice cream"

print("❓ USER:", user_query)
print("\n" + "-" * 65)
print("💬 RESPONSE:")
print("-" * 65)

# Analyze the meal components
pizza_carbs = 60   # 2-3 slices
beer_carbs = 20    # 2 beers
ice_cream = 25     # 2 scoops
total_carbs = pizza_carbs + beer_carbs + ice_cream

# Exercise impact (walking in heat)
exercise_minutes = 120
exercise_drop = exercise_minutes * patient_config.exercise_drop_factor

# Pizza has fat - delayed spike
fat_delay_hours = patient_config.fat_delay_hours

# Alcohol effect
alcohol_suppression = -8  # mg/dL

print(f"\n🍕 PIZZA + 🍺 BEER + 🍨 ICE CREAM Analysis:")
print(f"\n• Total carbs: {total_carbs}g")
print(f"• Recommended bolus: {total_carbs/patient_config.carb_ratio:.1f} units")
print(f"\n⚠️  COMPLEXITY FACTORS:")
print(f"   - {exercise_minutes} min walking (from sightseeing) = ~{exercise_drop:.0f} mg/dL drop")
print(f"   - Alcohol in beer = delayed hypo risk 4-8 hours later")
print(f"   - Pizza fat = delayed spike in {fat_delay_hours:.1f} hours")
print(f"   - Heat + exercise + alcohol = high delayed hypo risk")

# Find similar meals in history
similar = find_similar_meals("pizza")
if similar:
    print(f"\n📊 SIMILAR MEALS FROM YOUR HISTORY:")
    for entry in similar[:2]:
        print(f"   • {entry['carb_estimate_g']}g carbs → {entry['bolus_units']}U bolus")
        impact = entry.get('cgm_impact', {})
        print(f"     Result: {impact.get('peak_delta', '?')} mg/dL rise, {impact.get('peak_time_min', '?')}min")

print(f"\n💡 RECOMMENDATIONS:")
print(f"1. Split bolus: 60% now ({total_carbs/patient_config.carb_ratio*0.6:.1f}U), 40% extended")
print(f"2. Prebolus 10 min (you're running good glucose)")
print(f"3. Set reminder: Check BG 3-5hr post-meal for fat spike")
print(f"4. Have fast-acting carbs ready for 4-8hr when alcohol hits")

# Safety note per API pattern
print("\n---")
print("*Educational info, not medical advice. Discuss with your healthcare team.*")