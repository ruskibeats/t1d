/** @jsxImportSource @emotion/react */
import { useState, useEffect, useCallback } from 'react'
import axios from 'axios'
import { SleepEntry } from '@/types'
import { demoSleepEntries as demoSleep } from '@/lib/demoData'

export function useSleep() {
  const [entries, setEntries] = useState<SleepEntry[]>(demoSleep)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const fetchEntries = useCallback(async (start?: string, end?: string) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      setEntries(demoSleep)
      setDemoMode(true)
      return
    }
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const response = await axios.get(`/api/v1/sleep?${params}`)
      const data = Array.isArray(response.data) ? response.data : []
      setEntries(data.length > 0 ? data : demoSleep)
      setDemoMode(data.length === 0)
    } catch {
      setEntries(demoSleep)
      setDemoMode(true)
    } finally {
      setLoading(false)
    }
  }, [])

  const createEntry = async (data: Partial<SleepEntry>) => {
    try {
      const response = await axios.post('/api/v1/sleep', data)
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: SleepEntry = {
        id: Date.now(), user_id: 1,
        start_time: data.start_time || new Date().toISOString(),
        end_time: data.end_time, duration_minutes: data.duration_minutes,
        score: data.score, efficiency: data.efficiency, source: 'manual',
      }
      setEntries(prev => [fallback, ...prev])
      setDemoMode(true)
      return fallback
    }
  }

  useEffect(() => {
    const end = new Date().toISOString()
    const start = new Date(Date.now() - 7 * 24 * 60 * 60_000).toISOString()
    fetchEntries(start, end)
  }, [fetchEntries])

  const avgDuration = entries.length > 0
    ? Math.round(entries.reduce((s, e) => s + (e.duration_minutes || 0), 0) / entries.length) : 0
  const avgQuality = entries.filter(e => e.score).length > 0
    ? Math.round(entries.filter(e => e.score).reduce((s, e) => s + (e.score || 0), 0) / entries.filter(e => e.score).length) : 0

  return { entries, loading, demoMode, fetchEntries, createEntry, avgDuration, avgQuality }
}
