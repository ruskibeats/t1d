import { ContextEvent, GlucoseReading } from '@/types'

const now = Date.now()

function wave(index: number) {
  return Math.sin(index / 4) * 18 + Math.cos(index / 11) * 10
}

export const demoReadings: GlucoseReading[] = Array.from({ length: 96 }, (_, index) => {
  const minutesAgo = index * 30
  const hour = new Date(now - minutesAgo * 60_000).getHours()
  const mealLift = hour === 8 || hour === 13 || hour === 20 ? 42 : 0
  const overnightDip = hour >= 1 && hour <= 4 ? -18 : 0
  const exerciseDip = hour === 18 ? -24 : 0
  const value = Math.round(128 + wave(index) + mealLift + overnightDip + exerciseDip)

  return {
    id: 10_000 + index,
    user_id: 1,
    glucose_value: Math.max(58, Math.min(236, value)),
    timestamp: new Date(now - minutesAgo * 60_000).toISOString(),
    source: index % 8 === 0 ? 'manual' : 'dexcom',
  }
})

export const demoEvents: ContextEvent[] = [
  {
    id: 1,
    user_id: 1,
    event_type: 'meal',
    timestamp: new Date(now - 70 * 60_000).toISOString(),
    description: 'Oat bowl, berries, coffee',
    carbs_grams: 52,
    protein_grams: 18,
    fat_grams: 14,
    calories: 430,
  },
  {
    id: 2,
    user_id: 1,
    event_type: 'insulin',
    timestamp: new Date(now - 92 * 60_000).toISOString(),
    description: 'Meal bolus logged',
    insulin_units: 4.2,
    insulin_type: 'rapid',
  },
  {
    id: 3,
    user_id: 1,
    event_type: 'exercise',
    timestamp: new Date(now - 18 * 60 * 60_000).toISOString(),
    description: 'Zone 2 run',
    duration: 32,
    intensity: 'moderate',
  },
  {
    id: 4,
    user_id: 1,
    event_type: 'sleep',
    timestamp: new Date(now - 8 * 60 * 60_000).toISOString(),
    description: '7h 20m, one gentle low trend',
    duration: 440,
  },
  {
    id: 5,
    user_id: 1,
    event_type: 'stress',
    timestamp: new Date(now - 26 * 60 * 60_000).toISOString(),
    description: 'High workload afternoon',
  },
]

export function calculateStats(readings: GlucoseReading[] = demoReadings) {
  const values = readings.map((reading) => reading.glucose_value)
  const total = values.length || 1
  const average = values.reduce((sum, value) => sum + value, 0) / total
  const min = Math.min(...values)
  const max = Math.max(...values)
  const variance = values.reduce((sum, value) => sum + Math.pow(value - average, 2), 0) / total
  const inRange = values.filter((value) => value >= 70 && value <= 180).length
  const below = values.filter((value) => value < 70).length
  const above = values.filter((value) => value > 180).length

  return {
    average,
    min_value: min,
    max_value: max,
    std_dev: Math.sqrt(variance),
    total_readings: readings.length,
    time_in_range: {
      percentage: (inRange / total) * 100,
      below_range: { percentage: (below / total) * 100 },
      above_range: { percentage: (above / total) * 100 },
    },
  }
}

export const demoPatternAnalysis = {
  analysis: {
    grade: 'B',
    tir: calculateStats().time_in_range,
    estimated_a1c: '6.9',
  },
  statistics: calculateStats(),
}

export const demoSpikes = [
  {
    meal: { food_name: 'Friday pizza', carbs: 78 },
    severity: 'moderate',
    glucose_rise: 62,
    peak_value: 214,
    timing: '3h 20m after meal',
  },
  {
    meal: { food_name: 'Cereal breakfast', carbs: 64 },
    severity: 'mild',
    glucose_rise: 44,
    peak_value: 188,
    timing: '1h 10m after meal',
  },
]

export const demoExerciseImpacts = [
  {
    exercise: { intensity: 'moderate', exercise_type: 'run', duration_minutes: 32 },
    impact: { avg_change_from_baseline: -38 },
  },
  {
    exercise: { intensity: 'low', exercise_type: 'walk', duration_minutes: 25 },
    impact: { avg_change_from_baseline: -16 },
  },
]

export const demoOvernight = [
  {
    date: new Date(now - 2 * 24 * 60 * 60_000).toISOString(),
    percentage_of_night: 8.5,
    lowest_value: 64,
  },
]
