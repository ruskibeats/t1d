// Hook for fetching and managing proactive insights

import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'

export interface TimeOfDayPattern {
  type: string
  severity: 'low' | 'moderate' | 'high'
  hour: number
  hour_range: string
  description: string
  detail: string
  confidence: number
  data_points: number
  avg_value: number
  recommendation: string
  disclaimer: string
}

export interface MealPattern {
  type: string
  severity: 'low' | 'moderate' | 'high'
  food_name: string
  occurrences: number
  description: string
  detail: string
  confidence: number
  avg_peak_glucose: number
  avg_time_to_peak_min: number
  recommendation: string
  disclaimer: string
}

export interface PreMealPrediction {
  food_name: string
  based_on_meals: number
  predicted_peak: number
  predicted_time_to_peak_min: number
  message: string
  current_status?: string
  recommendation: string
  disclaimer: string
}

export interface GlucoseSummary {
  period: string
  total_readings: number
  avg_glucose: number
  time_in_range_pct: number
  min_glucose: number
  max_glucose: number
}

export interface InsightsData {
  generated_at: string
  summary: GlucoseSummary | null
  time_of_day_patterns: TimeOfDayPattern[]
  meal_patterns: MealPattern[]
  total_insights: number
  disclaimer: string
}

export function useInsights() {
  const [insights, setInsights] = useState<InsightsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchInsights = useCallback(async () => {
    try {
      setLoading(true)
      const res = await axios.get('/api/v1/insights')
      setInsights(res.data)
      setError(null)
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? 'Failed to load insights')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchInsights()
  }, [fetchInsights])

  const predictMeal = useCallback(async (foodName: string, currentGlucose?: number): Promise<PreMealPrediction | null> => {
    try {
      const res = await axios.post('/api/v1/insights/predict', {
        food_name: foodName,
        current_glucose: currentGlucose ?? null,
      })
      return res.data
    } catch (err: any) {
      return null
    }
  }, [])

  return { insights, loading, error, fetchInsights, predictMeal }
}