#!/usr/bin/env python3
"""
Combined HUPA-UCM + OhioT1DM Calibration
Uses HUPA-UCM for well-controlled/brittle patterns, OhioT1DM for food/glucose alignment.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

OUTPUT_FILE = Path("/root/t1d/calibration/output/combined_calibration.json")

def parse_hupa_ucm():
    """Extract features from HUPA-UCM dataset."""
    data_dir = Path("/root/t1d/hupaucm/HUPA-UCM Diabetes Dataset/Preprocessed")
    features = {}
    
    for csv_file in sorted(data_dir.glob("*.csv")):
        patient_id = csv_file.stem
        try:
            df = pd.read_csv(csv_file, sep=';')
            df['time'] = pd.to_datetime(df['time'])
            df = df.set_index('time')
            
            glucose = df['glucose'].dropna()
            
            features[patient_id] = {
                'tir_70_180': ((glucose >= 70) & (glucose <= 180)).mean(),
                'variability_cv': (glucose.std() / glucose.mean()) * 100,
                'mean_glucose': glucose.mean(),
                'overnight_low_rate': glucose.between_time('00:00', '06:00').lt(70).mean(),
                'spike_rate': (glucose > 200).mean(),
                'bolus_frequency': (df['bolus_volume_delivered'].fillna(0) > 0).mean() * 24 * 60 / 5,
            }
        except Exception as e:
            print(f"Error processing {patient_id}: {e}")
    
    return features

def parse_ohiot1dm():
    """Extract food-glucose correlation data from OhioT1DM."""
    data_dir = Path("/root/t1d/data/diabetes_subset_pictures-glucose-food-insulin")
    food_glucose_data = []
    
    for patient_dir in sorted(data_dir.glob("*")):
        if not patient_dir.is_dir() or patient_dir.name.startswith('.'):
            continue
        
        patient_id = patient_dir.name
        
        try:
            # Load food data
            food_file = patient_dir / "food.csv"
            if not food_file.exists():
                continue
            
            food_df = pd.read_csv(food_file)
            food_df['datetime'] = pd.to_datetime(food_df['datetime'], format='%Y:%m:%d %H:%M:%S')
            
            # Load glucose data
            glucose_file = patient_dir / "glucose.csv"
            if not glucose_file.exists():
                continue
            
            glucose_df = pd.read_csv(glucose_file)
            glucose_df['datetime'] = pd.to_datetime(glucose_df['date'] + ' ' + glucose_df['time'])
            glucose_df['glucose'] = glucose_df['glucose'] * 18.018  # mmol/L to mg/dL
            
            # Match food to glucose responses
            for _, row in food_df.iterrows():
                food_time = row['datetime']
                # Get glucose 2-4 hours post-meal for primary response
                window = glucose_df[
                    (glucose_df['datetime'] >= food_time) &
                    (glucose_df['datetime'] <= food_time + pd.Timedelta(hours=4))
                ]
                
                if len(window) > 0:
                    food_glucose_data.append({
                        'patient_id': patient_id,
                        'food_desc': row['description'],
                        'calories': row['calories'],
                        'balance': row['balance'],
                        'quality': row['quality'],
                        'pre_meal_glucose': window.iloc[0]['glucose'] if len(window) > 0 else None,
                        'peak_glucose': window['glucose'].max(),
                        'glucose_rise': window['glucose'].max() - window.iloc[0]['glucose'] if len(window) > 0 else None,
                    })
        except Exception as e:
            print(f"Error processing OhioT1DM {patient_id}: {e}")
    
    return food_glucose_data

def main():
    print("Parsing HUPA-UCM dataset...")
    hupa_features = parse_hupa_ucm()
    print(f"  Extracted features for {len(hupa_features)} patients")
    
    print("Parsing OhioT1DM dataset...")
    ohiot1dm_data = parse_ohiot1dm()
    print(f"  Extracted {len(ohiot1dm_data)} food-glucose records")
    
    # Calculate high-fat meal patterns
    high_fat_meals = [d for d in ohiot1dm_data if 'cheese' in d['food_desc'].lower() or 
                      'bread' in d['food_desc'].lower() or 'pasta' in d['food_desc'].lower() or
                      'meat' in d['food_desc'].lower() or 'steak' in d['food_desc'].lower()]
    
    if high_fat_meals:
        avg_fat_delay = np.mean([d['glucose_rise'] for d in high_fat_meals if d['glucose_rise']])
        print(f"  High-fat meal avg glucose rise: {avg_fat_delay:.1f} mg/dL")
    
    # Save combined results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({
            'hupa_ucm_features': hupa_features,
            'ohiot1dm_food_glucose': ohiot1dm_data,
            'high_fat_analysis': {
                'count': len(high_fat_meals),
                'avg_glucose_rise': np.mean([d['glucose_rise'] for d in high_fat_meals if d['glucose_rise']]) if high_fat_meals else 0
            }
        }, f, indent=2, default=str)
    
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()