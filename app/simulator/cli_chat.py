#!/usr/bin/env python3
"""
T1D Companion Simulator CLI - Natural Language Interface

Usage: python -m app.simulator.cli_chat

Talk to the simulator like you would ask a diabetes educator.
"""

import json
from pathlib import Path
from app.simulator.schemas import AnchorType
from app.simulator.patient_factory import generate_patient_config

class T1DSimulatorCLI:
    def __init__(self, anchor_type=AnchorType.POST_MEAL_SPIKE, seed=42):
        self.config = generate_patient_config(anchor_type, seed)
        self.anchor = anchor_type.value.replace('_', ' ').title()
        self.history_path = Path("/root/t1d/data/food_history_90d.json")
        self.load_history()
        
    def load_history(self):
        if self.history_path.exists():
            with open(self.history_path) as f:
                self.history = json.load(f)[:2000]  # Limit memory
    
    def analyze_query(self, query: str) -> str:
        """Natural language analysis of food/insulin questions."""
        q = query.lower()
        
        # Pizza analysis
        if 'pizza' in q:
            carbs = 60
            fat_delay = int(self.config.fat_delay_hours)
            bolus = carbs / self.config.carb_ratio
            return f"""🍕 PIZZA ANALYSIS:
• Carbs: ~{carbs}g
• Bolus: {bolus:.1f} units
• Delayed spike: {fat_delay} hours (high fat)
• Recommendation: Split bolus 60/40, prebolus 10 min"""
        
        # Beer/alcohol
        if 'beer' in q or 'alcohol' in q:
            return """🍺 ALCOHOL IMPACT:
• Suppresses liver glucose output
• Risk of delayed hypo (4-8 hours)
• With exercise = higher risk
• Have carbs ready before bed"""
        
        # Exercise
        if 'walk' in q or 'exercise' in q or 'sightsee' in q:
            mins = 120  # default estimate
            if 'all day' in q:
                mins = 180
            drop = int(mins * self.config.exercise_drop_factor)
            return f"""🚶 EXERCISE IMPACT:
• Walking {mins} min = ~{drop} mg/dL drop
• Pre-meal exercise = more insulin sensitivity
• Post-meal = faster carb clearance"""
        
        # Ice cream
        if 'ice cream' in q or 'dessert' in q:
            return """🍨 ICE CREAM:
• Quick spike 30-60 min
• No fat delay like pizza
• Count all carbs including sugar alcohols if present"""
        
        # Default response
        return self.basic_meal_analysis(query)
    
    def basic_meal_analysis(self, query: str) -> str:
        """Basic carb/bolus estimate."""
        return f"""Based on your {self.anchor} profile:
• Carb ratio: 1U per {self.config.carb_ratio:.1f}g
• Insulin sensitivity: {self.config.insulin_sensitivity:.0f} mg/dL per U
• Exercise drop: {self.config.exercise_drop_factor:.1f} mg/dL per min

Tell me more about what you're eating/drinking!"""

def main():
    import sys
    
    print("=" * 60)
    print("🤖 T1D Simulator Chat - Natural Language Mode")
    print("=" * 60)
    print("Type 'quit' to exit.\n")
    
    cli = T1DSimulatorCLI()
    print(f"Patient type: {cli.anchor}")
    print(f"Config: CR={cli.config.carb_ratio:.1f}, IS={cli.config.insulin_sensitivity:.0f} mg/dL/U\n")
    
    # Default to Italy scenario for demo
    test_query = "I am on holiday in italy, it is 32 degrees outside and I am walking around sightseeing all day, I want to eat some pizza, drink some beers and have ice cream"
    
    print(f"You: {test_query}")
    print(f"\nSimulator: {cli.analyze_query(test_query)}")
    
    print("\n" + "-" * 60)
    print("\nTry your own query:")
    
    while True:
        try:
            query = input("\n> ").strip()
            if query.lower() in ('quit', 'exit', 'q'):
                break
            if query:
                print(f"\n{cli.analyze_query(query)}")
        except (EOFError, KeyboardInterrupt):
            break
    
    print("\nGoodbye!")

if __name__ == "__main__":
    main()