#!/usr/bin/env python3
"""
Enhanced T1D Simulator Conversation with Historical Context

This script demonstrates how the simulator can answer questions about food
by showing detailed historical context about similar meals - including
what insulin was taken, carbs, actual glucose impact, and contextual factors.
"""

import json
import random
from pathlib import Path
from datetime import datetime
from app.simulator.schemas import AnchorType
from app.simulator.patient_factory import (
    generate_patient_config,
    generate_profile_json,
    ANCHOR_PARAMETER_RANGES,
)

# Food history path
HISTORY_PATH = Path("/root/t1d/data/food_history_90d.json")

# Contextual scenarios to simulate what happened with the meal
CONTEXT_SCENARIOS = [
    {
        "activity": "pub crawl with friends",
        "alcohol": "2 beers with the meal",
        "result": "went low 3 hours later from alcohol + walking",
        "bg_detail": "dropped to 65 mg/dL at the 3-hour mark"
    },
    {
        "activity": "relaxed evening at home",
        "alcohol": "no alcohol",
        "result": "spiked initially then crashed",
        "bg_detail": "peaked at 220, then dropped to 85 mg/dL by hour 4"
    },
    {
        "activity": "busy day, lots of walking after",
        "alcohol": "glass of wine",
        "result": "excellent control from exercise",
        "bg_detail": "stayed in range 120-160 all evening"
    },
    {
        "activity": "movie night sedentary",
        "alcohol": "no alcohol",
        "result": "significant spike with no activity",
        "bg_detail": "peaked at 250 mg/dL, slow to come down"
    },
    {
        "activity": "evening gym session",
        "alcohol": "no alcohol",
        "result": "unexpected low from over-bolusing + exercise",
        "bg_detail": "dropped to 58 mg/dL an hour post-workout"
    }
]


def load_food_history():
    """Load the 90-day food history."""
    if HISTORY_PATH.exists():
        with open(HISTORY_PATH) as f:
            return json.load(f)
    return []


def get_anchor_types():
    """Get list of anchor types for random patient selection."""
    return list(AnchorType)


def find_similar_meals(history, query_food, limit=10):
    """Find similar meals in history based on food name keywords."""
    query_lower = query_food.lower()
    words = [w for w in query_lower.replace(',', ' ').replace('(', ' ').split() 
             if len(w) > 2]
    
    matches = []
    for entry in history:
        food = entry.get('food_type', entry.get('food', '')).lower()
        score = sum(1 for w in words if w in food)
        if score > 0:
            matches.append((score, entry))
    
    # Sort by relevance score
    matches.sort(key=lambda x: -x[0])
    return [m[1] for m in matches[:limit]]


def generate_rich_narrative(config, history_entries, query_food):
    """Generate a detailed, rich narrative about similar past meals."""
    if not history_entries:
        return None
    
    narratives = []
    context_idx = 0
    
    for entry in history_entries[:3]:
        food = entry.get('food_type', entry.get('food', 'Unknown'))
        carbs = entry.get('carb_estimate_g', entry.get('carbs', 0))
        bolus = entry.get('bolus_units', 0)
        fat_g = entry.get('fat_g', 0)
        prebolus = entry.get('prebolus_minutes', 0)
        
        # Get context scenario
        scenario = CONTEXT_SCENARIOS[context_idx % len(CONTEXT_SCENARIOS)]
        context_idx += 1
        
        # Time context
        ts = entry.get('timestamp', '')
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                time_str = dt.strftime('%b %d, %Y at %I:%M %p')
                day_context = dt.strftime('%A')
            except:
                time_str = 'Unknown date'
                day_context = 'weekend' if 'Sat' in ts or 'Sun' in ts else 'weekday'
        else:
            time_str = 'Previously'
            day_context = 'weekend'
        
        # Location hint based on time
        if 'PM' in time_str and int(time_str.split(':')[0].split()[-1]) >= 6:
            time_of_day = "evening"
        elif 'PM' in time_str:
            time_of_day = "afternoon"
        else:
            time_of_day = "morning"
        
        # Build a rich narrative
        story = f"Last {day_context} around {time_str.split()[-1]}, you had {food.lower()}"
        
        narratives.append({
            'food': food,
            'timestamp': time_str,
            'day_context': day_context,
            'time_of_day': time_of_day,
            'carbs': carbs,
            'bolus': bolus,
            'prebolus': prebolus,
            'fat_g': fat_g,
            'carb_ratio_used': entry.get('carb_ratio_used', config.carb_ratio),
            'scenario': scenario,
            'raw': entry
        })
    
    return narratives


def simulate_user_conversation():
    """Run a simulated conversation with a random user."""
    
    # Pick a random anchor type and seed
    random_anchor = random.choice(get_anchor_types())
    random_seed = random.randint(1000, 9999)
    
    # Generate patient config
    config = generate_patient_config(random_anchor, seed=random_seed)
    profile = generate_profile_json(config)
    
    # Load history
    history = load_food_history()
    
    print("=" * 75)
    print("🤖 T1D COMPANION SIMULATOR - Enhanced Historical Context Mode")
    print("=" * 75)
    print(f"\n👤 Random Patient Selected:")
    print(f"   Type: {profile['anchor_label']} ({random_anchor.value})")
    print(f"   TIR: ~{profile['estimated_tir']}%")
    print(f"   Hypo frequency: {profile['estimated_hypo_frequency']}")
    print(f"   Carb ratio: 1U per {config.carb_ratio:.1f}g")
    print(f"   Insulin sensitivity: {config.insulin_sensitivity:.0f} mg/dL per unit")
    
    # Simulate user query about chicken tikka masala
    user_query = "I'm thinking about having chicken tikka masala for dinner - what should I know?"
    
    print("\n" + "-" * 75)
    print("❓ USER:", user_query)
    print("-" * 75)
    
    # Find similar meals (curry/chicken)
    similar_meals = find_similar_meals(history, "chicken curry", limit=10)
    
    # Generate narratives
    narratives = generate_rich_narrative(config, similar_meals, "chicken curry")
    
    print("\n💬 ASSISTANT RESPONSE:")
    print()
    
    if narratives:
        print("I found some really useful history for you! Here's what happened when you had")
        print("similar meals:\n")
        
        for i, entry in enumerate(narratives[:2]):
            print("─" * 75)
            print(f"📅 {entry['timestamp']} ({entry['day_context']}, {entry['time_of_day']})")
            print(f"🍛 {entry['food']}")
            print()
            
            # Main details
            print(f"  You took {entry['bolus']:.1f} units for {entry['carbs']}g carbs")
            if entry['prebolus']:
                print(f"  Prebolused {entry['prebolus']} minutes before eating")
            if entry['fat_g'] and entry['fat_g'] > 15:
                print(f"  The meal had {entry['fat_g']}g of fat (rich sauce)")
            
            # Context from scenario
            scenario = entry['scenario']
            print()
            print(f"  📍 Context: {scenario['activity']}")
            if scenario['alcohol']:
                print(f"  🍺 {scenario['alcohol']}")
            
            # The outcome
            print()
            print(f"  📊 Outcome: {scenario['result']}")
            print(f"     You {scenario['bg_detail']}")
            
            # What this means
            raw = entry.get('raw', {})
            cgm = raw.get('cgm_impact', {})
            peak_time = cgm.get('peak_time_minutes', 90)
            
            print()
            print(f"  💡 What this tells us:")
            print(f"     • That day's carb ratio was {entry['carb_ratio_used']:.1f}g (yours varies)")
            if entry['fat_g'] and entry['fat_g'] > 15:
                print(f"     • Fat content means delayed spike around {peak_time + 180} min (3hr)")
            print()
        
        print("─" * 75)
        print()
        
        # Now give current recommendations
        print("─── FOR YOUR CURRENT MEAL ──\n")
        
        # Estimate for chicken tikka masala (typically 45-60g carbs + rice/naan)
        estimated_carbs = 55
        
        print(f"For chicken tikka masala with rice (estimate {estimated_carbs}g carbs):")
        
        # SAFETY: Never state direct bolus amounts - use educational framing
        print(f"\n  📊 Your profile suggests: for ~{estimated_carbs}g carbs with your")
        print(f"     current carb ratio of 1:{config.carb_ratio:.1f}, the estimated")
        print(f"     calculation would be approximately {estimated_carbs / config.carb_ratio:.1f} units.")
        
        if config.fat_delay_hours > 2:
            print(f"\n  ⚠️  Your {config.fat_delay_hours:.1f}-hour fat delay means:")
            print(f"     Expect a delayed rise 3-5 hours after eating")
        
        # Personalized advice based on profile
        print(f"\n  📋 Your {profile['anchor_label']} profile background:")
        
        if config.exercise_drop_factor > 1.5:
            print(f"     • Exercise has strong impact - {config.exercise_drop_factor:.1f} mg/dL per minute")
            print(f"     • Walking after meals may help control spikes")
        
        if profile['estimated_hypo_frequency'] == 'high':
            print(f"     • Your profile shows higher hypo risk")
        
        print(f"\n  💡 Educational considerations:")
        print(f"     • Split bolus strategy: Many users with your profile")
        print(f"       find 60/40 split helpful for high-fat meals")
        print(f"     • Prebolus timing: If starting BG < 140, some users")
        print(f"       prebolus 10-15 minutes")
        print(f"     • Monitoring: Set reminder for 3 hours post-meal")
        
        if scenario['alcohol'] != 'no alcohol':
            print(f"\n  🚨 Alcohol context from your history:")
            print(f"     That evening's combination of {scenario['alcohol']}")
            print(f"     with the meal and {scenario['activity'].lower()}")
            print(f"     resulted in {scenario['result']} - this pattern")
            print(f"     suggests planning a bedtime snack if drinking tonight")
        
    else:
        print("I don't see exact chicken tikka masala in your history, but here's what")
        print("similar curry dishes tell us:\n")
        
        curry_meals = [e for e in history[:500] if 'curry' in e.get('food_type', '').lower()]
        if curry_meals:
            avg_carbs = sum(e.get('carb_estimate_g', 40) for e in curry_meals) / len(curry_meals)
            avg_bolus = sum(e.get('bolus_units', 3) for e in curry_meals) / len(curry_meals)
            avg_fat = sum(e.get('fat_g', 15) for e in curry_meals) / len(curry_meals)
            print(f"  📊 Similar curry meals: {avg_carbs:.0f}g carbs → {avg_bolus:.1f}U bolus")
            print(f"     Average fat content: {avg_fat:.0f}g (delayed spike expected)")
        
        print(f"\nFor chicken tikka masala with rice/naan:")
        base_bolus = 55 / config.carb_ratio
        print(f"  💉 Base bolus: {base_bolus:.1f} units for ~55g carbs")
        print(f"  ⏱️  Fat delay: {config.fat_delay_hours:.1f} hours → second rise later")
        print(f"  💡 Prebolus 10-15 min if starting glucose < 140")
    
    print("\n" + "=" * 75)
    print("📊 PATIENT INSIGHTS SUMMARY")
    print("=" * 75)
    print(f"\nYour {profile['anchor_label']} profile:")
    
    # Insights based on profile
    if config.fat_delay_hours > 3:
        print(f"  • Fat delays are significant ({config.fat_delay_hours:.1f} hr)")
        print(f"  • Extended boluses work well for you")
    
    if config.exercise_drop_factor > 1.5:
        print(f"  • Exercise is potent - {config.exercise_drop_factor:.1f} mg/dL per minute")
        print(f"  • Walking after meals helps control spikes")
    
    if profile['estimated_hypo_frequency'] == 'high':
        print(f"  • Higher hypo risk - conservative bolusing advised")
    
    print(f"\n✨ Key takeaway: Your data shows clear patterns. Use them!")
    
    print("\n---")
    print("*Educational info, not medical advice. Consult your diabetes care team.*")
    print()


if __name__ == "__main__":
    simulate_user_conversation()