from pydantic import BaseModel, Field
from datetime import datetime
import json
import os

from app.db.models import User, GlucoseReading
from app.db.base import Base

class SyntheticDataGenerator:
    """
    Service to generate and save synthetic user data.
    """
    def __init__(self, output_dir="data/synthetic"):
        self.output_dir = output_dir

    def generate_synthetic_user(self, user_id):
        # Implementation to generate a synthetic user dictionary
        return {
            "user_id": user_id,
            "email": f"synthetic_{user_id}@example.com",
            "diabetes_type": "Type 1",
            "glucose_units": "mg/dL",
            "target_range_low": 70.0,
            "target_range_high": 180.0
        }

    def generate_synthetic_glucose(self, user_id, num_days=7):
        # Leveraging the generation logic from the exploration script
        import numpy as np
        from datetime import timedelta
        
        base_glucose = np.random.normal(140, 30)
        data = []
        start_time = datetime.now() - timedelta(days=num_days)
        
        for i in range(num_days * 24 * 12):
            timestamp = start_time + timedelta(minutes=i*5)
            glucose_value = base_glucose + np.random.normal(0, 15) + 10 * np.sin(i / 12)
            
            data.append({
                "timestamp": timestamp.isoformat(),
                "glucose_value": round(max(40, glucose_value), 2),
                "reading_type": "sensor",
                "source": "dexcom"
            })
        return data

    def save_data(self, user_id, profile, glucose_data):
        user_dir = os.path.join(self.output_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        
        with open(os.path.join(user_dir, "profile.json"), "w") as f:
            json.dump(profile, f, indent=4)
        with open(os.path.join(user_dir, "glucose.json"), "w") as f:
            json.dump(glucose_data, f, indent=4)
        print(f"Saved synthetic for {user_id}")
