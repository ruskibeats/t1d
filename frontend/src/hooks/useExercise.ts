/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface ExerciseEntry {
  id: number
  type: string
  duration_minutes: number
  calories?: number
  heart_rate_avg?: number
  start_time: string
  intensity?: string
  source: string
}

const demoExercises: ExerciseEntry[] = [
  { id: 1, type: 'running', duration_minutes: 30, calories: 280, heart_rate_avg: 145, start_time: new Date(Date.now() - 86400000).toISOString(), intensity: 'moderate', source: 'demo' },
  { id: 2, type: 'cycling', duration_minutes: 45, calories: 350, heart_rate_avg: 130, start_time: new Date(Date.now() - 172800000).toISOString(), intensity: 'moderate', source: 'demo' },
  { id: 3, type: 'walking', duration_minutes: 20, calories: 90, heart_rate_avg: 95, start_time: new Date(Date.now() - 259200000).toISOString(), intensity: 'low', source: 'demo' },
]

export function useExercise() {
  const [entries, setEntries] = useState<ExerciseEntry[]>(demoExercises)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const createEntry = async (data: Omit<ExerciseEntry, 'id'>) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const fallback: ExerciseEntry = { ...data, id: Date.now() }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
    try {
      const response = await axios.post('/api/v1/exercise', data)
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: ExerciseEntry = { ...data, id: Date.now() }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
  }

  const listEntries = async (start?: string, end?: string) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setEntries(demoExercises); return }
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (start) params.set('start', start); if (end) params.set('end', end)
      const response = await axios.get(`/api/v1/exercise?${params.toString()}`)
      const next = Array.isArray(response.data) ? response.data : []
      setEntries(next.length ? next : demoExercises)
      setDemoMode(next.length === 0)
    } catch { setEntries(demoExercises) }
    finally { setLoading(false) }
  }

  useEffect(() => { listEntries() }, [])
  return { entries, loading, demoMode, createEntry, listEntries }
}
