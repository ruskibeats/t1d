#!/usr/bin/env python3
"""Interactive simulator session for natural language Q&A."""

import json
from datetime import datetime
from app.simulator.schemas import AnchorType
from app.simulator.patient_factory import generate_patient_config
from app.simulator.anchors import ANCHOR_PARAMETER_RANGES

# Create a sample patient - let's pick POST_MEA_SPIKE for interesting dynamics
patient_config = generate_patient_config(AnchorType.POST_MEAL_SPIKE, seed=42)

def estimate_meal_impact(food_desc: str, carbs_g: float, alcohol_g: float = 0, 
                         exercise_minutes: float = 0, current_bg: float = 120) -> dict:
    """Estimate glucose impact from a meal based on patient parameters."""
    config = patient_config
    
    # Carb impact
    carb_spike = carbs_g * config.meal_rise_factor
    
    # Insulin recommendation
    carb_ratio = config.carb_ratio
    bolus = carbs_g / carb_ratio
    
    # Alcohol effect (suppresses gluconeogenesis, can cause delayed lows)
    alcohol_effect = -alcohol_g * 0.3  # mg/dL drop
    alcohol_delay_2hr = exercise_minutes > 30  # prolonged exercise effect
    
    # Exercise effect (walking in heat)
    exercise_drop = exercise_minutes * config.exercise_drop_factor
    
    # Net expected peak
    expected_peak = current_bg + carb_spike - (bolus * config.insulin_sensitivity * 0.1)
    
    # Timing
    if "pizza" in food_desc.lower() or "pasta" in food_desc.lower():
        peak_time = "60-90 min for initial, 3-5 hr for fat delayed"
        delayed_spike = carbs_g * 0.3 * config.meal_rise_factor  # 30% delayed
    else:
        peak_time = "60-90 min"
        delayed_spike = 0
    
    # Risk assessment
    hypo_risk = "moderate" if bolus > carbs_g / config.carb_ratio * 0.8 else "low"
    
    # Pre-bolus recommendation
    if config.basal_glucose_mean < 130:
        prebolus_min = 10
    else:
        prebolus_min = 0  # don't prebolus if running higher
    
    return {
        "meal": food_desc,
        "carb_estimate": f"{carbs_g}g",
        "bolus_recommendation": f"{bolus:.1f} units",
        "expected_peak": f"{expected_peak:.0f} mg/dL at {peak_time}",
        "current_bg": f"{current_bg} mg/dL",
        "factors": {
            "exercise_drop": f"-{exercise_drop:.0f} mg/dL (from {exercise_minutes} min walking)",
            "alcohol_effect": f"{alcohol_effect:.0f} mg/dL suppression",
            "delayed_fat_spike": f"+{delayed_spike:.0f} mg/dL (3-5hr post-meal)" if delayed_spike else "none"
        },
        "prebolus": f"{prebolus_min} min before meal",
        "hypo_risk": hypo_risk,
        "notes": []
    }

def simulate_patient():
    """Interactive session with the patient simulator."""
    print("=" * 60)
    print("SIMULATOR SESSION: Italian Holiday Meal Planning")
    print("=" * 60)
    print(f"\nPatient Profile: {patient_config.anchor_type.value.upper()}")
    print(f"  - Carb Ratio: 1 unit per {patient_config.carb_ratio}g carbs")
    print(f"  - Insulin Sensitivity: {patient_config.insulin_sensitivity} mg/dL per unit")
    print(f"  - Meal Rise Factor: {patient_config.meal_rise_factor} mg/dL per gram carb")
    print(f"  - Exercise Drop: {patient_config.exercise_drop_factor} mg/dL per minute")
    print(f"  - Fat Delay: {patient_config.fat_delay_hours} hr for high-fat meals")
    
    print("\n" + "-" * 60)
    print("YOUR QUERY: 'I am on holiday in italy, it is 32 degrees outside")
    print("and I am walking around sightseeing all day, I want to eat some")
    print("pizza, drink some beers and have ice cream'")
    print("-" * 60)
    
    # Estimate based on typical Italian meal
    pizza_carbs = 60  # 2-3 slices
    beer_carbs = 20   # 2 beers ~ 10g each
    ice_cream_carbs = 25  # 2 scoops
    total_carbs = pizza_carbs + beer_carbs + ice_cream_carbs
    alcohol_grams = 25  # 2 standard beers
    exercise_mins = 120  # sightseeing all day
    current_bg = 130  # reasonable starting point
    
    # Pizza impact
    print("\n🍕 PIZZA (high-carb + high-fat):")
    pizza = estimate_meal_impact("pizza with cheese", pizza_carbs, 
                                  current_bg=current_bg)
    print(f"  Carbs: {pizza_carbs}g")
    print(f"  Recommended bolus: {pizza['bolus_recommendation']}")
    print(f"  Expected peak: {pizza['expected_peak']}")
    print(f"  Pre-bolus: {pizza['prebolus']} min")
    print(f"  Risk: {pizza['hypo_risk']} hypoglycemia")
    
    # Beer impact
    print("\n🍺 BEER (alcohol + moderate carbs):")
    beer = estimate_meal_impact("beer", beer_carbs, alcohol_g=25,
                                 exercise_minutes=exercise_mins,
                                 current_bg=current_bg + 30)
    print(f"  Carbs: {beer_carbs}g, Alcohol: {alcohol_grams}g")
    print(f"  Recommended bolus: {beer['bolus_recommendation']}")
    print(f"  Alcohol effect: {beer['factors']['alcohol_effect']} (can cause delayed hypo)")
    print(f"  Exercise from walking: {beer['factors']['exercise_drop']}")
    
    # Ice cream impact
    print("\n🍨 ICE CREAM (high sugar, no fat delay):")
    ice_cream = estimate_meal_impact("ice cream", ice_cream_carbs,
                                      current_bg=current_bg + 20)
    print(f"  Carbs: {ice_cream_carbs}g")
    print(f"  Recommended bolus: {ice_cream['bolus_recommendation']}")
    
    print("\n" + "=" * 60)
    print("OVERALL RECOMMENDATIONS:")
    total_bolus = (pizza_carbs + beer_carbs + ice_cream_carbs) / patient_config.carb_ratio
    print(f"  Total carbs: {total_carbs}g")
    print(f"  Total bolus: {total_bolus:.1f} units")
    print(f"  ⚠️  HIGH RISK: Heat + exercise + alcohol = potential delayed hypo")
    print(f"  ⚠️  PIZZA: 3-5 hour delayed spike from fat content")
    print(f"  💡 Suggest: Split bolus 60% upfront, 40% extended")
    print(f"  💡 Suggest: Snack ready for 4-6hr post-meal (alcohol drop)")
    print("=" * 60)
    
    # Show what happens if they ask about similar past meals
    print("\n📊 SIMULATOR MEMORY (past similar meals):")
    from pathlib import Path
    history_file = Path("/root/t1d/data/food_history_90d.json")
    if history_file.exists():
        with open(history_file) as f:
            history = json.load(f)
        pizza_meals = [m for m in history[:500] if 'pizza' in m.get('food_type', '').lower()]
        if pizza_meals:
            m = pizza_meals[0]
            print(f"  Previous pizza: {m['carb_estimate_g']}g carbs, bolus={m['bolus_units']}U")
            print(f"  Result: {m.get('cgm_impact', {}).get('peak_delta', '?')} mg/dL rise")

if __name__ == "__main__":
    simulate_patient()