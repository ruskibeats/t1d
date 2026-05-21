import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

# Create data directory
DATA_DIR = "data/synthetic"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_synthetic_user_profile(user_id):
    """
    Generates a realistic synthetic T1D user profile.
    """
    return {
        "user_id": user_id,
        "diabetes_type": "Type 1",
        "glucose_units": "mg/dL",
        "target_range_low": 70.0,
        "target_range_high": 180.0,
        "created_at": datetime.now().isoformat()
    }

def generate_synthetic_glucose_data(user_id, num_days=7):
    """
    Generates realistic sensor glucose data for a synthetic user.
    """
    # Simulate a baseline glucose level
    base_glucose = np.random.normal(140, 30)
    
    data = []
    start_time = datetime.now() - timedelta(days=num_days)
    
    for i in range(num_days * 24 * 12): # 5-minute intervals
        timestamp = start_time + timedelta(minutes=i*5)
        # Add some random oscillation around baseline
        glucose_value = base_glucose + np.random.normal(0, 15) + 10 * np.sin(i / 12)
        
        data.append({
            "timestamp": timestamp.isoformat(),
            "glucose_value": round(max(40, glucose_value), 2),
            "reading_type": "sensor",
            "source": "dexcom"
        })
    
    return data

def save_synthetic_data(user_id, profile, glucose_data):
    user_dir = os.path.join(DATA_DIR, f"user_{user_id}")
    os.makedirs(user_dir, exist_ok=True)
    
    with open(os.path.join(user_dir, "profile.json"), "w") as f:
        json.dump(profile, f, indent=4)
        
    pd.DataFrame(glucose_data).to_json(os.path.join(user_dir, "glucose.json"), orient="records", indent=4)
    print(f"Generated data for user {user_id} in {user_dir}")

# Generate a small pool
for i in range(1, 4):
    profile = generate_synthetic_user_profile(i)
    glucose = generate_synthetic_glucose_data(i)
    save_synthetic_data(i, profile, glucose)
