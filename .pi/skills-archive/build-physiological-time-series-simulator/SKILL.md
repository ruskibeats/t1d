---
name: "build-physiological-time-series-simulator"
description: "Build a discrete time-step physiological signal simulator with composable component effects (circadian, meal/medication, exercise, noise). Use when you need synthetic time-series data to stress-test pattern detectors, validate algorithms, or generate training data for physiological signals like glucose, heart rate, or blood pressure."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Build a Physiological Time-Series Simulator

## When to Use

Build a discrete time-step simulator for physiological signals (glucose, heart rate, blood pressure, etc.) when you need synthetic time-series data to:
- Stress-test pattern detection algorithms against known ground truth
- Validate algorithm behavior across diverse patient profiles
- Generate training data for ML models
- Prototype UI components without needing real data

Do NOT use when you need a single patient's data for a quick test — use a deterministic seed or a seeder script instead.

## Architecture

The simulation follows a **composable component model** at discrete time steps:

```
for each time_step in simulation_period:
    value += circadian_component(time_step)      # baseline rhythm
    value += meal_component(active_meals)        # perturbation
    value += medication_component(active_doses)  # clearance
    value += exercise_component(active_sessions) # temporary effect
    value += recovery_drift(value, target)       # homeostasis
    value += stochastic_noise(value)             # sensor/biological noise
    record(value)
```

## Step 1 — Define Patient Config / Anchor Profiles

Create typed config objects with physiological parameters:

```python
@dataclass
class PatientConfig:
    target_baseline: float       # e.g., 120 mg/dL for glucose
    meal_rise_factor: float      # carb sensitivity
    medication_sensitivity: float
    exercise_drop_rate: float
    circadian_amplitude: float   # strength of daily rhythm
    circadian_peak_hour: int     # when rhythm peaks (0-23)
    recovery_rate: float         # how fast signal returns to baseline
    noise_std: float             # sensor noise as % of current value
    body_weight: float           # distribution volume (kg)
```

Group related profiles into "anchors" representing archetypes:

```python
ANCHORS = {
    "typical": {target_baseline: 120, meal_rise_factor: 0.08, ...},
    "high_variance": {target_baseline: 140, meal_rise_factor: 0.15, ...},
    "athlete": {target_baseline: 100, exercise_drop_rate: 0.04, ...},
}
```

**Pitfall**: Keep profiles distinct enough to produce measurably different simulation outputs. Small differences in parameters vanish in noise if all profiles are too similar.

## Step 2 — Build a Day Context Generator

Generate daily event schedules as inputs to the simulation:

```python
@dataclass
class MealEvent:
    time_min: int        # minutes from midnight
    magnitude: float     # e.g., carb grams
    
@dataclass
class MedicationEvent:
    time_min: int
    dose: float
    
@dataclass
class ExerciseEvent:
    time_min: int
    duration_min: int
    intensity: float

class DayContextGenerator:
    def generate_day(self, config, rng, day_index) -> DayContext:
        # Randomized but deterministic (seeded RNG) event schedule
        # 3 meals + snacks, medication doses, exercise sessions
```

**Pitfall**: Random hour generation — `randint(22, 24)` returns 24 which is invalid. Always use `randint(22, 23)` for bounded hour ranges.

## Step 3 — Build the Simulation Engine

The core loop. Each step computes **delta = sum of all component effects**:

```python
class SimulationEngine:
    STEP_MINUTES = 5  # sampling interval
    MIN_VALUE = 0.0   # physiological floor (e.g., glucose can't go negative)
    
    def simulate(self, config, day_context, rng, days=1):
        total_minutes = days * 24 * 60
        readings = []
        value = config.target_baseline
        
        for minute in range(0, total_minutes, self.STEP_MINUTES):
            # 1. Circadian baseline
            value += self._circadian_rhythm(config, minute)
            
            # 2. Drift toward target (homeostasis)
            value += (config.target_baseline - value) * config.recovery_rate * self.STEP_MINUTES
            
            # 3. Perturbation effects
            for meal in day_context.active_meals(minute):
                value += self._meal_absorption(meal, config)
            
            # 4. Medication clearance
            for dose in day_context.active_medications(minute):
                value -= self._medication_effect(dose, config)
            
            # 5. Exercise effect
            for ex in day_context.active_exercise(minute):
                value -= self._exercise_effect(ex, config)
            
            # 6. Clamp to physiologically plausible range
            value = max(self.MIN_VALUE, value)
            
            # 7. Add noise
            noisy = value + rng.gauss(0, abs(value) * config.noise_std)
            
            readings.append((minute, max(self.MIN_VALUE, noisy)))
        
        return readings
```

Component functions should be **pure** — they compute delta for one time step based on the event model:

```python
def _circadian_rhythm(self, config, minute):
    """Sinusoidal daily rhythm peaking at config.circadian_peak_hour."""
    hour = (minute / 60) % 24
    phase = 2 * math.pi * (hour - config.circadian_peak_hour) / 24
    return config.circadian_amplitude * math.sin(phase) * self.STEP_MINUTES / 60

def _meal_absorption(self, meal, config):
    """Gaussian-like rise peaking ~30-45 min post-meal, decay over ~3h."""
    minutes_since_meal = minute - meal.time_min
    peak_time = 30  # minutes
    duration = 180  # total absorption window
    if 0 <= minutes_since_meal < duration:
        gaussian = math.exp(-((minutes_since_meal - peak_time) ** 2) / (2 * (duration/4) ** 2))
        return meal.magnitude * config.meal_rise_factor * gaussian * self.STEP_MINUTES
    return 0.0
```

### Pitfalls

- **Prevent divergence**: Always include a drift-toward-target (homeostasis) term. Without it, accumulated perturbation effects will cause the signal to drift to implausible values or diverge entirely.
- **Clamp at physiological floor**: Most biological signals cannot go below zero. Clamp after each step to prevent negative values that would break downstream detectors.
- **Caching active events per minute**: If there are many events (e.g., 90 days × 3 meals/day = 270 meals), iterating all events at each minute step (1440/5 = 288 steps/day × 270 meals = 77k checks) is slow. Build an index: `events_by_minute = {minute: [events_active_at(minute)]}` precomputed before the main loop.
- **Noise level matters**: Too much noise drowns patterns (detectors can't detect anything). Too little noise makes detection trivially easy. Set noise_std so that signal-to-noise ratio is realistic — typically 3-8% of current value for sensor data.
- **5-minute exact spacing**: Ensure CGM readings are spaced exactly STEP_MINUTES apart. Off-by-one errors in minute calculation compound over many days.

## Step 4 — Multi-Day Simulation With Reproducibility

```python
engine = SimulationEngine(config, rng, days=90)
for day in range(days):
    day_context = generator.generate_day(config, rng, day)
    readings = engine.simulate_day(day_context, day)
    all_readings.extend(readings)
```

Seed reproducibility:
- Derive each patient's seed from a combination of run_id and patient_index
- Use `seed = run_id * 10000 + patient_index * 100`
- Log seeds for later reconstruction

**Pitfall**: Don't reuse the same `rng` across patients without re-seeding — the second patient will get different seeds deterministically, but if you reorder anchors, all downstream results change. Always derive seed from a stable identifier.

## Step 5 — Verification

```bash
# Verify no negative values
python3 -c "
readings = simulate(config, day_context, rng, 90)
assert all(g >= 0 for _, g in readings), 'Negative readings!'
"

# Verify circadian rhythm produces expected pattern
python3 -c "
# For a target=120 config, pre-dawn should be near target,
# post-meal should rise above 180, overnight should stay above 70
readings = simulate(config, day_context, rng, 1)
pre_dawn = [g for t, g in readings if 180 <= t <= 300]
post_meal = [g for t, g in readings if t >= meal_time and t <= meal_time+120]
assert max(post_meal) > 180 if has_large_meal else True
assert min(pre_dawn) > 70
"

# Verify reproducibility
python3 -c "
rng1 = random.Random(42); rng2 = random.Random(42)
r1 = simulate(config, day_context, rng1, 1)
r2 = simulate(config, day_context, rng2, 1)
assert r1 == r2, 'Not reproducible!'
"

# Verify step count is exact
python3 -c "
readings = simulate(config, day_context, rng, 1)
assert len(readings) == 24 * 60 / 5, f'Expected 288 readings, got {len(readings)}'
"
```

## Boundary Conditions

- **Should use**: When building any time-step physiological simulation where composable component effects matter — glucose, heart rate, blood pressure, SpO2, temperature.
- **Should use**: When the simulation needs to produce data for multiple patient/archetype profiles with distinct parameter ranges.
- **Do NOT use**: For non-physiological time series (stock prices, weather, sensor noise). Use an appropriate domain-specific model instead.
- **Do NOT use**: When you need continuous (non-discrete) simulation or sub-second fidelity. This pattern is for 1-15 minute sampled physiological data.