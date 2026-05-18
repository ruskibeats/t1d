"""MetricType enum — single source of truth for all health metric types."""

from enum import StrEnum


class GraphEdgeType(StrEnum):
    """Relationship types between health metric nodes.

    Edges are observational evidence, not medical advice. They describe
    temporal/correlational relationships that pattern detection found.
    """

    MEAL_TO_GLUCOSE_SPIKE = "meal_to_glucose_spike"
    MEAL_TO_DELAYED_SPIKE = "meal_to_delayed_spike"
    EXERCISE_TO_GLUCOSE_DROP = "exercise_to_glucose_drop"
    EXERCISE_TO_GLUCOSE_RISE = "exercise_to_glucose_rise"
    INSULIN_TO_GLUCOSE_CHANGE = "insulin_to_glucose_change"
    SLEEP_TO_NEXT_DAY_GLUCOSE = "sleep_to_next_day_glucose"
    STRESS_TO_GLUCOSE_RISE = "stress_to_glucose_rise"
    HEART_RATE_TO_LOW_GLUCOSE = "heart_rate_to_low_glucose"
    HYDRATION_TO_GLUCOSE_STABILITY = "hydration_to_glucose_stability"
    CORRELATES_WITH = "correlates_with"
    PRECEDES = "precedes"
    SAME_EVENT_AS = "same_event_as"


class MetricType(StrEnum):
    """All valid health metric type identifiers.

    Every metric stored in health_metrics uses one of these types.
    Add new types here when integrating new data sources.
    """

    # ── Glucose & Insulin ──
    BLOOD_GLUCOSE = "blood_glucose"
    INSULIN = "insulin"
    INSULIN_BASAL = "insulin_basal"
    INSULIN_BOLUS = "insulin_bolus"
    INSULIN_CORRECTION = "insulin_correction"
    CGM_TREND = "cgm_trend"
    ESTIMATED_A1C = "estimated_a1c"

    # ── Nutrition ──
    CARBS = "carbs"
    PROTEIN = "protein"
    FAT = "fat"
    FIBER = "fiber"
    CALORIES = "calories"
    GLYCEMIC_INDEX = "glycemic_index"
    GLYCEMIC_LOAD = "glycemic_load"
    WATER = "water"
    CAFFEINE = "caffeine"

    # ── Exercise ──
    EXERCISE_MINUTES = "exercise_minutes"
    EXERCISE_CALORIES = "exercise_calories"
    STEPS = "steps"
    DISTANCE_KM = "distance_km"
    FLOORS_CLIMBED = "floors_climbed"

    # ── Heart & Vitals ──
    HEART_RATE = "heart_rate"
    RESTING_HEART_RATE = "resting_heart_rate"
    HEART_RATE_VARIABILITY = "heart_rate_variability"
    SPO2 = "spo2"
    RESPIRATORY_RATE = "respiratory_rate"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"

    # ── Sleep ──
    SLEEP_HOURS = "sleep_hours"
    SLEEP_DEEP = "sleep_deep"
    SLEEP_REM = "sleep_rem"
    SLEEP_LIGHT = "sleep_light"
    SLEEP_AWAKE = "sleep_awake"
    SLEEP_SCORE = "sleep_score"
    SLEEP_LATENCY = "sleep_latency"
    BODY_BATTERY_CHANGE = "body_battery_change"
    AVG_SLEEP_STRESS = "avg_sleep_stress"

    # ── Body Composition ──
    WEIGHT = "weight"
    BODY_FAT_PERCENT = "body_fat_percent"
    BMI = "bmi"
    WAIST_CIRCUMFERENCE = "waist_circumference"
    LEAN_MASS = "lean_mass"

    # ── Fasting & Lifestyle ──
    FASTING_DURATION = "fasting_duration"
    MOOD_SCORE = "mood_score"
    STRESS_LEVEL = "stress_level"
    ENERGY_LEVEL = "energy_level"

    # ── Environment ──
    TEMPERATURE = "temperature"
    HUMIDITY = "humidity"
    ALTITUDE = "altitude"

    # ── Custom ──
    CUSTOM = "custom"

    @classmethod
    def glucose_types(cls) -> set["MetricType"]:
        return {cls.BLOOD_GLUCOSE, cls.CGM_TREND, cls.ESTIMATED_A1C}

    @classmethod
    def insulin_types(cls) -> set["MetricType"]:
        return {cls.INSULIN, cls.INSULIN_BASAL, cls.INSULIN_BOLUS, cls.INSULIN_CORRECTION}

    @classmethod
    def nutrition_types(cls) -> set["MetricType"]:
        return {cls.CARBS, cls.PROTEIN, cls.FAT, cls.FIBER, cls.CALORIES,
                cls.GLYCEMIC_INDEX, cls.GLYCEMIC_LOAD, cls.WATER, cls.CAFFEINE}

    @classmethod
    def exercise_types(cls) -> set["MetricType"]:
        return {cls.EXERCISE_MINUTES, cls.EXERCISE_CALORIES, cls.STEPS,
                cls.DISTANCE_KM, cls.FLOORS_CLIMBED}

    @classmethod
    def sleep_types(cls) -> set["MetricType"]:
        return {cls.SLEEP_HOURS, cls.SLEEP_DEEP, cls.SLEEP_REM, cls.SLEEP_LIGHT,
                cls.SLEEP_AWAKE, cls.SLEEP_SCORE, cls.SLEEP_LATENCY,
                cls.BODY_BATTERY_CHANGE, cls.AVG_SLEEP_STRESS}
