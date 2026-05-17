/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface MoodEntry {
  id: number
  score: number
  notes?: string
  logged_at: string
  source: string
}

const demoMoods: MoodEntry[] = [
  { id: 1, score: 7, notes: 'Feeling good today', logged_at: new Date(Date.now() - 86400000).toISOString(), source: 'demo' },
  { id: 2, score: 5, notes: 'A bit tired', logged_at: new Date(Date.now() - 172800000).toISOString(), source: 'demo' },
  { id: 3, score: 8, notes: 'Great mood!', logged_at: new Date(Date.now() - 259200000).toISOString(), source: 'demo' },
]

export function useMood() {
  const [entries, setEntries] = useState<MoodEntry[]>(demoMoods)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const createEntry = async (data: { score: number; notes?: string; logged_at?: string }) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const fallback: MoodEntry = { ...data, id: Date.now(), logged_at: data.logged_at || new Date().toISOString(), source: 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
    try {
      const response = await axios.post('/api/v1/mood', { ...data, logged_at: data.logged_at || new Date().toISOString() })
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: MoodEntry = { ...data, id: Date.now(), logged_at: data.logged_at || new Date().toISOString(), source: 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
  }

  const listEntries = async () => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setEntries(demoMoods); return }
    setLoading(true)
    try {
      const response = await axios.get('/api/v1/mood')
      const next = Array.isArray(response.data) ? response.data : []
      setEntries(next.length ? next : demoMoods)
      setDemoMode(next.length === 0)
    } catch { setEntries(demoMoods) }
    finally { setLoading(false) }
  }

  const getWeekAverage = () => {
    const weekEntries = entries.slice(0, 7)
    if (weekEntries.length === 0) return 0
    return weekEntries.reduce((sum, e) => sum + e.score, 0) / weekEntries.length
  }

  useEffect(() => { listEntries() }, [])
  return { entries, loading, demoMode, createEntry, listEntries, getWeekAverage }
}