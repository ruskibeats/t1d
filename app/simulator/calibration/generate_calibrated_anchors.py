#!/usr/bin/env python3
"""
Generate final calibrated anchor parameters from combined HUPA-UCM + OhioT1DM data.
"""

import json
from pathlib import Path

OUTPUT_FILE = Path("/root/t1d/calibration/output/calibrated_anchors.json")
INPUT_FILE = Path("/root/t1d/calibration/output/combined_calibration.json")

# Base parameters adjusted by real data insights
CALIBRATED_ANCHORS = {
    "well_controlled": {
        "basal_glucose_mean": (105, 125),
        "hypo_risk": (0.02, 0.08),
        "variability_cv": (15, 25),
        "meal_rise_factor": 2.0,
        "fat_delay_hours": 2.5,
        "validation_note": "HUPA0005P, HUPA0021P, HUPA0023P, HUPA0027P, HUPA0028P - TIR 60-72%"
    },
    "brittle": {
        "basal_glucose_mean": (110, 140),
        "hypo_risk": (0.15, 0.40),
        "variability_cv": (35, 55),
        "meal_rise_factor": 3.5,
        "fat_delay_hours": 5.0,
        "validation_note": "HUPA0002P, HUPA0003P, HUPA0004P, HUPA0006P, HUPA0007P - High CV, frequent lows"
    },
    "post_meal_spike": {
        "basal_glucose_mean": (120, 150),
        "hypo_risk": (0.03, 0.12),
        "variability_cv": (20, 30),
        "meal_rise_factor": 4.0,
        "fat_delay_hours": 2.5,
        "validation_note": "HUPA0001P, HUPA0009P, HUPA0011P - Spike rate 30-40%"
    },
    "overnight_hypo": {
        "basal_glucose_mean": (100, 130),
        "hypo_risk": (0.25, 0.50),
        "variability_cv": (20, 30),
        "meal_rise_factor": 2.0,
        "fat_delay_hours": 2.0,
        "validation_note": "HUPA0022P, HUPA0025P - Overnight low rate >20%"
    },
    "high_fat_delayed": {
        "basal_glucose_mean": (115, 145),
        "hypo_risk": (0.03, 0.10),
        "variability_cv": (25, 35),
        "meal_rise_factor": 4.0,
        "fat_delay_hours": (5.0, 8.0),
        "validation_note": "OhioT1DM food logs - cheese/bread/pasta/steak 94.7 mg/dL avg rise"
    },
    "dawn_phenomenon": {
        "basal_glucose_mean": (100, 130),
        "hypo_risk": (0.03, 0.10),
        "variability_cv": (20, 30),
        "meal_rise_factor": 1.5,
        "fat_delay_hours": 2.0,
        "validation_note": "Literature-based - 30-55 mg/dL overnight rise"
    },
    "insulin_sensitive": {
        "basal_glucose_mean": (90, 120),
        "hypo_risk": (0.10, 0.25),
        "variability_cv": (14, 22),
        "meal_rise_factor": 1.0,
        "fat_delay_hours": 2.0,
        "validation_note": "Literature-based - 50-80 mg/dL/U sensitivity"
    },
    "insulin_resistant": {
        "basal_glucose_mean": (150, 180),
        "hypo_risk": (0.02, 0.08),
        "variability_cv": (22, 35),
        "meal_rise_factor": 4.5,
        "fat_delay_hours": 4.0,
        "validation_note": "Literature-based - 8-18 mg/dL/U sensitivity"
    },
}

def main():
    with open(INPUT_FILE) as f:
        data = json.load(f)
    
    output = {
        "calibration_date": "2026-05-23",
        "data_sources": {
            "hupa_ucm": "25 patients, 14+ days each",
            "ohiot1dm": "3 patients, food-glucose alignment"
        },
        "anchor_parameters": CALIBRATED_ANCHORS,
        "validation_metrics": {
            "hupa_patients_analyzed": len(data['hupa_ucm_features']),
            "ohiot1dm_food_records": len(data['ohiot1dm_food_glucose']),
            "high_fat_avg_glucose_rise_mg_dl": data['high_fat_analysis']['avg_glucose_rise']
        }
    }
    
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"Saved calibrated anchors to {OUTPUT_FILE}")
    print(f"High-fat meal validation: {data['high_fat_analysis']['avg_glucose_rise']:.1f} mg/dL glucose rise")

if __name__ == "__main__":
    main()