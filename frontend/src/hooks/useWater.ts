/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface WaterEntry {
  id: number
  amount_ml: number
  logged_at: string
  source: string
}

const demoWater: WaterEntry[] = [
  { id: 1, amount_ml: 500, logged_at: new Date(Date.now() - 3600000).toISOString(), source: 'demo' },
  { id: 2, amount_ml: 750, logged_at: new Date(Date.now() - 7200000).toISOString(), source: 'demo' },
  { id: 3, amount_ml: 250, logged_at: new Date(Date.now() - 10800000).toISOString(), source: 'demo' },
]

export function useWater() {
  const [entries, setEntries] = useState<WaterEntry[]>(demoWater)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const createEntry = async (data: { amount_ml: number; logged_at?: string }) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const fallback: WaterEntry = { ...data, id: Date.now(), logged_at: data.logged_at || new Date().toISOString(), source: 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
    try {
      const response = await axios.post('/api/v1/water', { ...data, logged_at: data.logged_at || new Date().toISOString() })
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch {
      const fallback: WaterEntry = { ...data, id: Date.now(), logged_at: data.logged_at || new Date().toISOString(), source: 'manual' }
      setEntries(prev => [fallback, ...prev])
      return fallback
    }
  }

  const listEntries = async () => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) { setEntries(demoWater); return }
    setLoading(true)
    try {
      const response = await axios.get('/api/v1/water')
      const next = Array.isArray(response.data) ? response.data : []
      setEntries(next.length ? next : demoWater)
      setDemoMode(next.length === 0)
    } catch { setEntries(demoWater) }
    finally { setLoading(false) }
  }

  const getTodayTotal = () => {
    const today = new Date().toISOString().split('T')[0]
    return entries.filter(e => e.logged_at.startsWith(today)).reduce((sum, e) => sum + e.amount_ml, 0)
  }

  useEffect(() => { listEntries() }, [])
  return { entries, loading, demoMode, createEntry, listEntries, getTodayTotal }
}