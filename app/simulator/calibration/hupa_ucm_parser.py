#!/usr/bin/env python3
"""
HUPA-UCM Dataset Parser and Calibrator

Parses the HUPA-UCM preprocessed CSV files and extracts
features for calibrating simulator anchors.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

DATA_DIR = Path("/root/t1d/hupaucm/HUPA-UCM Diabetes Dataset/Preprocessed")
OUTPUT_FILE = Path("/root/t1d/calibration/output/calibration_params.json")

def parse_patient_file(filepath: Path) -> pd.DataFrame:
    """Parse a single HUPA-UCM patient CSV file."""
    df = pd.read_csv(filepath, sep=';')
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')
    return df

def calculate_phenotype_features(df: pd.DataFrame) -> dict:
    """Calculate key phenotype features from patient data."""
    glucose = df['glucose'].dropna()
    
    # Time in range (70-180 mg/dL)
    tir_70_180 = ((glucose >= 70) & (glucose <= 180)).mean()
    
    # Overnight low rate (00:00-06:00)
    overnight = glucose.between_time('00:00', '06:00')
    overnight_low_rate = (overnight < 70).mean()
    
    # Postprandial spike rate (glucose > 200 mg/dL)
    postprandial_spike_rate = (glucose > 200).mean()
    
    # Variability (CV of glucose)
    variability_cv = (glucose.std() / glucose.mean()) * 100
    
    # Mean glucose
    mean_glucose = glucose.mean()
    
    # Glucose amplitude estimate
    amplitude = glucose.max() - glucose.min()
    
    # Bolus frequency
    bolus_volume = df['bolus_volume_delivered'].fillna(0)
    bolus_frequency = (bolus_volume > 0).mean() * 24 * 60 / 5  # boluses per day
    
    return {
        'tir_70_180': round(tir_70_180, 3),
        'overnight_low_rate': round(overnight_low_rate, 3),
        'postprandial_spike_rate': round(postprandial_spike_rate, 3),
        'variability_cv': round(variability_cv, 1),
        'mean_glucose': round(mean_glucose, 1),
        'amplitude': round(amplitude, 1),
        'bolus_frequency_per_day': round(bolus_frequency, 1),
    }

def cluster_patients(features: dict) -> dict:
    """Map patients to anchor types based on features using detailed rules."""
    mapping = {}
    
    for patient_id, feats in features.items():
        tir = feats['tir_70_180']
        var = feats['variability_cv']
        overnight = feats['overnight_low_rate']
        spikes = feats['postprandial_spike_rate']
        mean_g = feats['mean_glucose']
        amplitude = feats['amplitude']
        bolus_freq = feats['bolus_frequency_per_day']
        
        # Detailed rule-based clustering
        if var > 40:
            anchor = 'brittle'
        elif overnight > 0.20 and tir < 0.65:
            anchor = 'overnight_hypo'
        elif spikes > 0.30:
            anchor = 'post_meal_spike'
        elif var > 35 and tir < 0.60:
            anchor = 'high_variability'
        elif tir > 0.70 and var < 30 and spikes < 0.15:
            anchor = 'well_controlled'
        elif mean_g > 180:
            anchor = 'insulin_resistant'
        elif mean_g < 120 and var < 30:
            anchor = 'insulin_sensitive'
        elif bolus_freq > 7:
            anchor = 'exercise_regimen'
        elif overnight > 0.15 and amplitude > 200:
            anchor = 'overnight_hypo'
        else:
            anchor = 'well_controlled'  # default
        
        mapping[patient_id] = anchor
    
    return mapping

def main():
    print("Parsing HUPA-UCM dataset...")
    
    all_features = {}
    
    for csv_file in sorted(DATA_DIR.glob("*.csv")):  # Process all 25 patients
        patient_id = csv_file.stem
        print(f"  Processing {patient_id}...")
        
        try:
            df = parse_patient_file(csv_file)
            features = calculate_phenotype_features(df)
            all_features[patient_id] = features
        except Exception as e:
            print(f"    Error: {e}")
    
    print(f"\nExtracted features for {len(all_features)} patients")
    
    # Cluster patients
    mapping = cluster_patients(all_features)
    print(f"Patient-ancon mapping: {mapping}")
    
    # Save results
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({'features': all_features, 'mapping': mapping}, f, indent=2)
    
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()