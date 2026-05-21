"""Detector version constants for graph edge provenance tracking."""

# Current version of each detector - bump when algorithm changes affect confidence scoring
DETECTOR_VERSIONS = {
    "meal_to_glucose_spike": "1.0.0",
    "exercise_to_hypoglycemia": "1.0.0",
    "sleep_to_morning_glucose": "1.0.0",
    "insulin_to_glucose_drop": "1.0.0",
    "high_fat_meal_delay": "1.0.0",
    "stress_to_glucose_elev": "1.0.0",
    "event_group_link": "1.0.0",
}

def get_detector_version(detector_name: str) -> str:
    """Get the current version for a detector."""
    return DETECTOR_VERSIONS.get(detector_name, "0.0.0")

def bump_detector_version(detector_name: str, version: str) -> None:
    """Update the version for a detector."""
    DETECTOR_VERSIONS[detector_name] = version