/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface MeasurementEntry {
  id: number
  metric_name: string
  value: number
  unit: string
  note?: string
  measured_at: string
  source: string
}

const demoMeasurements: MeasurementEntry[] = [
  { id: 1, metric_name: 'weight', value: 75.5, unit: 'kg', note: 'morning weigh-in', measured_at: new Date(Date.now() - 86400000).toISOString(), source: 'demo' },
  { id: 2, metric_name: 'body_fat', value: 18.5, unit: '%', note: 'bioelectrical impedance', measured_at: new Date(Date.now() - 86400000).toISOString(), source: 'demo' },
]

export function useMeasurements() {
  const [entries, setEntries] = useState<MeasurementEntry[]>(demoMeasurements)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const createEntry = async (data: { metric_name: string; value: number; unit: string; note?: string; source?: string }) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const fallback: MeasurementEntry = { ...data, id: Date.now(), measured_at: new Date().toISOString(), source: data.source || 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
    try {
      const response = await axios.post('/api/v1/measurements', data)
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: MeasurementEntry = { ...data, id: Date.now(), measured_at: new Date().toISOString(), source: data.source || 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
  }

  const listEntries = async (metricName?: string) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setEntries(demoMeasurements); return }
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (metricName) params.set('metric_name', metricName)
      const response = await axios.get(`/api/v1/measurements?${params.toString()}`)
      const next = Array.isArray(response.data) ? response.data : []
      setEntries(next.length ? next : demoMeasurements)
      setDemoMode(next.length === 0)
    } catch { setEntries(demoMeasurements) }
    finally { setLoading(false) }
  }

  useEffect(() => { listEntries() }, [])
  return { entries, loading, demoMode, createEntry, listEntries }
}