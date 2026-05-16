/** @jsxImportSource @emotion/react */
import { useState } from 'react'
import axios from 'axios'
import { addDays, formatISO } from 'date-fns'

export interface HealthMetricPoint {
  id: number
  metric_type: string
  value: number
  unit: string
  measured_at: string
  source: string
}

const demoMetrics: HealthMetricPoint[] = [
  // Glucose (24hrs)
  ...Array.from({ length: 48 }, (_, i) => ({
    id: i + 100,
    metric_type: 'blood_glucose' as const,
    value: 80 + Math.sin(i * 0.3) * 40 + Math.random() * 20,
    unit: 'mg/dL',
    measured_at: new Date(Date.now() - (47 - i) * 1800000).toISOString(),
    source: 'demo',
  })),
  // Exercise
  { id: 1, metric_type: 'exercise_minutes', value: 30, unit: 'minutes', measured_at: new Date(Date.now() - 3600000).toISOString(), source: 'demo' },
  { id: 2, metric_type: 'exercise_minutes', value: 45, unit: 'minutes', measured_at: new Date(Date.now() - 86400000).toISOString(), source: 'demo' },
  { id: 3, metric_type: 'exercise_minutes', value: 20, unit: 'minutes', measured_at: new Date(Date.now() - 172800000).toISOString(), source: 'demo' },
  // Sleep
  { id: 4, metric_type: 'sleep_hours', value: 7.5, unit: 'hours', measured_at: new Date(Date.now() - 43200000).toISOString(), source: 'demo' },
  { id: 5, metric_type: 'sleep_hours', value: 6.5, unit: 'hours', measured_at: new Date(Date.now() - 129600000).toISOString(), source: 'demo' },
  { id: 6, metric_type: 'sleep_hours', value: 8, unit: 'hours', measured_at: new Date(Date.now() - 216000000).toISOString(), source: 'demo' },
  // Calories
  { id: 7, metric_type: 'calories', value: 1800, unit: 'kcal', measured_at: new Date(Date.now() - 43200000).toISOString(), source: 'demo' },
  { id: 8, metric_type: 'calories', value: 2100, unit: 'kcal', measured_at: new Date(Date.now() - 129600000).toISOString(), source: 'demo' },
]

export function useHealthMetrics() {
  const [metrics, setMetrics] = useState<HealthMetricPoint[]>(demoMetrics)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const fetchMetrics = async (range: '1d' | '3d' | '7d' | '14d') => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setMetrics(demoMetrics); return }

    const days = { '1d': 1, '3d': 3, '7d': 7, '14d': 14 }
    const end = new Date()
    const start = addDays(end, -days[range])
    const params = new URLSearchParams({
      start: formatISO(start), end: formatISO(end),
      types: 'blood_glucose,exercise_minutes,sleep_hours,calories',
    })

    setLoading(true)
    try {
      const response = await axios.get(`/api/v1/metrics?${params.toString()}`)
      const next = Array.isArray(response.data) ? response.data : []
      setMetrics(next.length ? next : demoMetrics)
      setDemoMode(next.length === 0)
    } catch { setMetrics(demoMetrics) }
    finally { setLoading(false) }
  }

  return { metrics, loading, demoMode, fetchMetrics }
}
