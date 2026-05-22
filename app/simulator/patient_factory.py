"""Patient parameter generation from anchor profiles.

Given an anchor type and a seed, produces a concrete PatientConfig
by sampling uniformly within the anchor's parameter ranges.
"""

import random
from typing import Optional

from app.simulator.anchors import ANCHOR_PARAMETER_RANGES, anchor_description, anchor_label
from app.simulator.schemas import AnchorType, PatientConfig


def generate_patient_config(
    anchor_type: AnchorType,
    seed: int,
) -> PatientConfig:
    """Generate a concrete PatientConfig by sampling within an anchor's range.

    Args:
        anchor_type: The anchor archetype to sample from.
        seed: RNG seed for reproducibility.

    Returns:
        PatientConfig with deterministic parameter values.
    """
    rng = random.Random(seed)
    params = ANCHOR_PARAMETER_RANGES[anchor_type]

    def _rand(mn: float, mx: float) -> float:
        """Sample uniformly within [min, max], rounded to 2 decimal places."""
        return round(rng.uniform(mn, mx), 2)

    # Generate raw config from anchor ranges
    config = PatientConfig(
        anchor_type=anchor_type,
        seed=seed,
        basal_glucose_mean=_rand(*params.basal_glucose_mean),
        basal_glucose_amplitude=_rand(*params.basal_glucose_amplitude),
        meal_rise_factor=_rand(*params.meal_rise_factor),
        insulin_sensitivity=_rand(*params.insulin_sensitivity),
        carb_ratio=_rand(*params.carb_ratio),
        hypo_risk=_rand(*params.hypo_risk),
        noise_sd=_rand(*params.noise_sd),
        exercise_drop_factor=_rand(*params.exercise_drop_factor),
        dawn_effect_strength=_rand(*params.dawn_effect_strength),
        fat_delay_hours=_rand(*params.fat_delay_hours),
        variability_cv=_rand(*params.variability_cv),
    )

    # IMPORTANT: Compute meal_rise_factor to be self-consistent with
    # insulin_sensitivity and carb_ratio. This ensures the engine's
    # meal + insulin effects roughly balance so glucose returns to
    # baseline between meals instead of ratcheting up.
    #
    # For net ≈ 0: meal_rise ≈ insulin_sensitivity * 0.25 / carb_ratio
    # Multiply by BALANCE_FACTOR to control post-meal excursion size:
    #   1.0 = no net rise (returns exactly to baseline)
    #   1.5 = moderate rise (~50% above baseline)
    #   2.0 = large spike (post_meal_spike anchor)
    balance_factors = {
        AnchorType.WELL_CONTROLLED: 1.2,
        AnchorType.BRITTLE: 1.8,
        AnchorType.DAWN_PHENOMENON: 1.3,
        AnchorType.POST_MEAL_SPIKE: 2.0,
        AnchorType.OVERNIGHT_HYPO: 1.0,
        AnchorType.EXERCISE_REGIMEN: 1.2,
        AnchorType.HIGH_FAT_DELAYED: 1.5,
        AnchorType.HIGH_VARIABILITY: 1.6,
        AnchorType.INSULIN_RESISTANT: 1.3,
        AnchorType.INSULIN_SENSITIVE: 0.9,
        AnchorType.EXERCISE_SENSITIVE: 1.1,
        AnchorType.NEWLY_DIAGNOSED: 1.5,
    }
    bf = balance_factors.get(anchor_type, 1.3)
    computed_meal_rise = round(config.insulin_sensitivity * 0.25 / config.carb_ratio * bf, 2)

    # Recreate config with the computed meal_rise_factor (Pydantic model is frozen)
    return PatientConfig(
        anchor_type=config.anchor_type,
        seed=config.seed,
        basal_glucose_mean=config.basal_glucose_mean,
        basal_glucose_amplitude=config.basal_glucose_amplitude,
        meal_rise_factor=computed_meal_rise,
        insulin_sensitivity=config.insulin_sensitivity,
        carb_ratio=config.carb_ratio,
        hypo_risk=config.hypo_risk,
        noise_sd=config.noise_sd,
        exercise_drop_factor=config.exercise_drop_factor,
        dawn_effect_strength=config.dawn_effect_strength,
        fat_delay_hours=config.fat_delay_hours,
        variability_cv=config.variability_cv,
    )


def generate_profile_json(config: PatientConfig) -> dict:
    """Generate a human-readable profile dict for storage in sim_users.profile_json.

    Args:
        config: The patient's parameter config.

    Returns:
        Dict with profile metadata.
    """
    return {
        "anchor_type": config.anchor_type.value,
        "anchor_label": anchor_label(config.anchor_type),
        "description": anchor_description(config.anchor_type),
        "estimated_tir": _estimate_tir(config),
        "estimated_a1c": _estimate_a1c(config),
        "estimated_hypo_frequency": "high" if config.hypo_risk > 0.2 else "moderate" if config.hypo_risk > 0.1 else "low",
        "variability_category": "high" if config.variability_cv > 35 else "moderate" if config.variability_cv > 25 else "low",
    }


def generate_patient_batch(
    anchor_type: AnchorType,
    count: int,
    start_seed: int = 1000,
) -> list[PatientConfig]:
    """Generate multiple patient configs for the same anchor type.

    Args:
        anchor_type: The anchor archetype.
        count: Number of patients to generate.
        start_seed: Starting seed (each patient gets start_seed + i).

    Returns:
        List of PatientConfig instances.
    """
    return [
        generate_patient_config(anchor_type, start_seed + i)
        for i in range(count)
    ]


def _estimate_tir(config: PatientConfig) -> float:
    """Roughly estimate time-in-range from config parameters (0-100%)."""
    base_tir = 70.0
    # Higher mean pushes more readings above range
    if config.basal_glucose_mean > 160:
        base_tir -= 20
    elif config.basal_glucose_mean > 140:
        base_tir -= 10
    # Higher variability reduces TIR
    base_tir -= config.variability_cv * 0.3
    # Hypo risk
    base_tir -= config.hypo_risk * 25
    # Dawn effect
    base_tir -= config.dawn_effect_strength * 0.2
    return max(10, min(98, round(base_tir, 1)))


def _estimate_a1c(config: PatientConfig) -> float:
    """Roughly estimate A1C from config parameters."""
    # ~ (avg_glucose + 46.7) / 28.7
    avg_glucose = config.basal_glucose_mean + config.dawn_effect_strength * 0.3 + config.meal_rise_factor * 10
    return round((avg_glucose + 46.7) / 28.7, 1)
