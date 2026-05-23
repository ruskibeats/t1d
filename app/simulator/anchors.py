"""12 anchor profiles defining synthetic patient archetypes.

Each anchor is a named archetype with parameter ranges that control
glucose dynamics, event patterns, and planted truth labels.

Profiles are designed to stress-test the PatternService detectors
across realistic clinical variability.
"""

from app.simulator.schemas import AnchorParameterRange, AnchorType

# ── Profile Definitions ──

ANCHOR_PARAMETER_RANGES: dict[AnchorType, AnchorParameterRange] = {
    # 1) Well-controlled Type 1
    AnchorType.WELL_CONTROLLED: AnchorParameterRange(
        anchor_type=AnchorType.WELL_CONTROLLED,
        basal_glucose_mean=(100, 120),
        basal_glucose_amplitude=(10, 20),
        meal_rise_factor=(2.0, 3.0),
        insulin_sensitivity=(35, 55),
        carb_ratio=(10, 18),
        hypo_risk=(0.02, 0.08),
        noise_sd=(5, 10),
        exercise_drop_factor=(1.0, 2.0),
        dawn_effect_strength=(0, 5),
        fat_delay_hours=(2, 4),
        variability_cv=(15, 25),
    ),
    # 2) Brittle / erratic
    AnchorType.BRITTLE: AnchorParameterRange(
        anchor_type=AnchorType.BRITTLE,
        basal_glucose_mean=(100, 140),
        basal_glucose_amplitude=(25, 40),
        meal_rise_factor=(2.5, 4.5),
        insulin_sensitivity=(15, 35),
        carb_ratio=(5, 12),
        hypo_risk=(0.15, 0.40),
        noise_sd=(15, 28),
        exercise_drop_factor=(2.0, 4.5),
        dawn_effect_strength=(15, 40),
        fat_delay_hours=(3, 7),
        variability_cv=(35, 55),
    ),
    # 3) Dawn phenomenon dominant
    AnchorType.DAWN_PHENOMENON: AnchorParameterRange(
        anchor_type=AnchorType.DAWN_PHENOMENON,
        basal_glucose_mean=(100, 130),
        basal_glucose_amplitude=(10, 20),
        meal_rise_factor=(1.5, 2.5),
        insulin_sensitivity=(30, 50),
        carb_ratio=(10, 18),
        hypo_risk=(0.03, 0.10),
        noise_sd=(5, 10),
        exercise_drop_factor=(1.0, 2.0),
        dawn_effect_strength=(30, 55),
        fat_delay_hours=(2, 4),
        variability_cv=(20, 30),
    ),
    # 4) Post-meal spike dominant
    AnchorType.POST_MEAL_SPIKE: AnchorParameterRange(
        anchor_type=AnchorType.POST_MEAL_SPIKE,
        basal_glucose_mean=(100, 140),
        basal_glucose_amplitude=(10, 20),
        meal_rise_factor=(3.0, 5.0),
        insulin_sensitivity=(25, 45),
        carb_ratio=(8, 15),
        hypo_risk=(0.03, 0.12),
        noise_sd=(5, 10),
        exercise_drop_factor=(1.0, 2.5),
        dawn_effect_strength=(5, 15),
        fat_delay_hours=(2, 4),
        variability_cv=(20, 30),
    ),
    # 5) Overnight hypo prone
    AnchorType.OVERNIGHT_HYPO: AnchorParameterRange(
        anchor_type=AnchorType.OVERNIGHT_HYPO,
        basal_glucose_mean=(100, 130),
        basal_glucose_amplitude=(5, 15),
        meal_rise_factor=(1.5, 2.5),
        insulin_sensitivity=(40, 70),
        carb_ratio=(15, 25),
        hypo_risk=(0.25, 0.50),
        noise_sd=(5, 10),
        exercise_drop_factor=(2.0, 4.0),
        dawn_effect_strength=(5, 15),
        fat_delay_hours=(2, 4),
        variability_cv=(20, 30),
    ),
    # 6) Exercise sensitive
    AnchorType.EXERCISE_SENSITIVE: AnchorParameterRange(
        anchor_type=AnchorType.EXERCISE_SENSITIVE,
        basal_glucose_mean=(100, 130),
        basal_glucose_amplitude=(10, 20),
        meal_rise_factor=(1.5, 2.5),
        insulin_sensitivity=(30, 50),
        carb_ratio=(10, 18),
        hypo_risk=(0.05, 0.15),
        noise_sd=(5, 10),
        exercise_drop_factor=(3.0, 5.0),
        dawn_effect_strength=(5, 15),
        fat_delay_hours=(2, 4),
        variability_cv=(18, 28),
    ),
    # 7) High-fat delayed spike
    AnchorType.HIGH_FAT_DELAYED: AnchorParameterRange(
        anchor_type=AnchorType.HIGH_FAT_DELAYED,
        basal_glucose_mean=(100, 130),
        basal_glucose_amplitude=(10, 20),
        meal_rise_factor=(2.0, 3.5),
        insulin_sensitivity=(25, 45),
        carb_ratio=(8, 16),
        hypo_risk=(0.03, 0.10),
        noise_sd=(5, 10),
        exercise_drop_factor=(1.0, 2.5),
        dawn_effect_strength=(5, 15),
        fat_delay_hours=(4, 8),
        variability_cv=(20, 30),
    ),
    # 8) Insulin sensitive
    AnchorType.INSULIN_SENSITIVE: AnchorParameterRange(
        anchor_type=AnchorType.INSULIN_SENSITIVE,
        basal_glucose_mean=(90, 120),
        basal_glucose_amplitude=(8, 18),
        meal_rise_factor=(1.0, 1.8),
        insulin_sensitivity=(50, 80),
        carb_ratio=(18, 28),
        hypo_risk=(0.10, 0.25),
        noise_sd=(4, 8),
        exercise_drop_factor=(2.0, 4.0),
        dawn_effect_strength=(0, 8),
        fat_delay_hours=(2, 3),
        variability_cv=(14, 22),
    ),
    # 9) Insulin resistant
    AnchorType.INSULIN_RESISTANT: AnchorParameterRange(
        anchor_type=AnchorType.INSULIN_RESISTANT,
        basal_glucose_mean=(140, 180),
        basal_glucose_amplitude=(15, 25),
        meal_rise_factor=(2.5, 4.0),
        insulin_sensitivity=(8, 18),
        carb_ratio=(5, 10),
        hypo_risk=(0.02, 0.08),
        noise_sd=(8, 15),
        exercise_drop_factor=(0.5, 1.5),
        dawn_effect_strength=(10, 25),
        fat_delay_hours=(3, 6),
        variability_cv=(22, 35),
    ),
    # 10) High variability
    AnchorType.HIGH_VARIABILITY: AnchorParameterRange(
        anchor_type=AnchorType.HIGH_VARIABILITY,
        basal_glucose_mean=(110, 160),
        basal_glucose_amplitude=(20, 35),
        meal_rise_factor=(2.0, 4.0),
        insulin_sensitivity=(20, 50),
        carb_ratio=(8, 20),
        hypo_risk=(0.10, 0.30),
        noise_sd=(15, 28),
        exercise_drop_factor=(1.5, 4.0),
        dawn_effect_strength=(10, 35),
        fat_delay_hours=(2, 6),
        variability_cv=(35, 55),
    ),
    # 11) Exercise regimen (frequent, structured exercise)
    AnchorType.EXERCISE_REGIMEN: AnchorParameterRange(
        anchor_type=AnchorType.EXERCISE_REGIMEN,
        basal_glucose_mean=(90, 120),
        basal_glucose_amplitude=(8, 18),
        meal_rise_factor=(1.0, 2.0),
        insulin_sensitivity=(35, 55),
        carb_ratio=(12, 22),
        hypo_risk=(0.05, 0.12),
        noise_sd=(5, 10),
        exercise_drop_factor=(1.5, 3.0),
        dawn_effect_strength=(0, 10),
        fat_delay_hours=(2, 4),
        variability_cv=(15, 25),
    ),
    # 12) Newly diagnosed
    AnchorType.NEWLY_DIAGNOSED: AnchorParameterRange(
        anchor_type=AnchorType.NEWLY_DIAGNOSED,
        basal_glucose_mean=(110, 150),
        basal_glucose_amplitude=(15, 30),
        meal_rise_factor=(2.5, 4.5),
        insulin_sensitivity=(15, 35),
        carb_ratio=(5, 12),
        hypo_risk=(0.08, 0.25),
        noise_sd=(10, 20),
        exercise_drop_factor=(1.0, 3.0),
        dawn_effect_strength=(10, 30),
        fat_delay_hours=(2, 5),
        variability_cv=(28, 45),
    ),
}


def list_anchor_profiles() -> list[AnchorParameterRange]:
    """Return all anchor profile parameter ranges."""
    return list(ANCHOR_PARAMETER_RANGES.values())


def get_anchor_range(anchor_type: AnchorType) -> AnchorParameterRange:
    """Get the parameter range for a specific anchor type."""
    return ANCHOR_PARAMETER_RANGES[anchor_type]


def anchor_label(anchor_type: AnchorType) -> str:
    """Human-readable label for an anchor type."""
    labels = {
        AnchorType.WELL_CONTROLLED: "Well-Controlled",
        AnchorType.BRITTLE: "Brittle / Erratic",
        AnchorType.DAWN_PHENOMENON: "Dawn Phenomenon",
        AnchorType.POST_MEAL_SPIKE: "Post-Meal Spike Dominant",
        AnchorType.OVERNIGHT_HYPO: "Overnight Hypo Prone",
        AnchorType.EXERCISE_SENSITIVE: "Exercise Sensitive",
        AnchorType.HIGH_FAT_DELAYED: "High-Fat Delayed Spike",
        AnchorType.INSULIN_SENSITIVE: "Insulin Sensitive",
        AnchorType.INSULIN_RESISTANT: "Insulin Resistant",
        AnchorType.HIGH_VARIABILITY: "High Variability",
        AnchorType.EXERCISE_REGIMEN: "Exercise Regimen",
        AnchorType.NEWLY_DIAGNOSED: "Newly Diagnosed",
    }
    return labels.get(anchor_type, anchor_type.value)


def anchor_description(anchor_type: AnchorType) -> str:
    """Description of what makes this anchor profile unique."""
    descriptions = {
        AnchorType.WELL_CONTROLLED: "Stable glucose with good time-in-range, minimal extremes.",
        AnchorType.BRITTLE: "High glycemic variability with unpredictable swings and frequent extremes.",
        AnchorType.DAWN_PHENOMENON: "Significant early-morning glucose rise requiring elevated basal rates overnight.",
        AnchorType.POST_MEAL_SPIKE: "Pronounced glucose rises after meals, especially high-carb meals.",
        AnchorType.OVERNIGHT_HYPO: "Frequent nocturnal hypoglycemia with extended low periods during sleep.",
        AnchorType.EXERCISE_SENSITIVE: "Dramatic glucose drops during and after physical activity.",
        AnchorType.HIGH_FAT_DELAYED: "Delayed glucose peaks 4-8 hours after high-fat meals.",
        AnchorType.INSULIN_SENSITIVE: "Very responsive to small insulin doses with risk of over-correction.",
        AnchorType.INSULIN_RESISTANT: "Requires high insulin doses with blunted post-meal response.",
        AnchorType.HIGH_VARIABILITY: "Unpredictable glucose swings across all time periods.",
        AnchorType.EXERCISE_REGIMEN: "Well-controlled with consistent daily exercise routine.",
        AnchorType.NEWLY_DIAGNOSED: "Higher average glucose, learning-phase variability, and inconsistent dosing.",
    }
    return descriptions.get(anchor_type, "")
