/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface FastingEntry {
  id: number
  start_time: string
  end_time: string | null
  duration_minutes: number | null
  source: string
}

const demoEntries: FastingEntry[] = [
  { id: 1, start_time: new Date(Date.now() - 172800000).toISOString(), end_time: new Date(Date.now() - 86400000).toISOString(), duration_minutes: 1440, source: 'demo' },
  { id: 2, start_time: new Date(Date.now() - 432000000).toISOString(), end_time: new Date(Date.now() - 259200000).toISOString(), duration_minutes: 172800, source: 'demo' },
]

export function useFasting() {
  const [entries, setEntries] = useState<FastingEntry[]>(demoEntries)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const createEntry = async (data: { start_time: string; end_time?: string; duration_minutes?: number; source?: string }) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const fallback: FastingEntry = { ...data, id: Date.now(), end_time: data.end_time || null, duration_minutes: data.duration_minutes || null, source: data.source || 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
    try {
      const response = await axios.post('/api/v1/fasting', data)
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: FastingEntry = { ...data, id: Date.now(), end_time: data.end_time || null, duration_minutes: data.duration_minutes || null, source: data.source || 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
  }

  const listEntries = async (start?: string, end?: string) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setEntries(demoEntries); return }
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (start) params.set('start', start); if (end) params.set('end', end)
      const response = await axios.get(`/api/v1/fasting?${params.toString()}`)
      const next = Array.isArray(response.data) ? response.data : []
      setEntries(next.length ? next : demoEntries)
      setDemoMode(next.length === 0)
    } catch { setEntries(demoEntries) }
    finally { setLoading(false) }
  }

  useEffect(() => { listEntries() }, [])
  return { entries, loading, demoMode, createEntry, listEntries }
}