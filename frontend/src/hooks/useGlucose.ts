/** @jsxImportSource @emotion/react */
import { useState, useCallback } from 'react'
import axios from 'axios'
import { GlucoseReading } from '@/types'
import { calculateStats, demoReadings } from '@/lib/demoData'

const API_BASE = '/api/v1'

type NormalizedStats = ReturnType<typeof calculateStats>

function normalizeStats(raw: any, readings: GlucoseReading[]): NormalizedStats {
  if (!raw) return calculateStats(readings)

  if (raw.time_in_range && typeof raw.time_in_range === 'object') {
    return raw
  }

  return {
    average: raw.average ?? 0,
    min_value: raw.min_value ?? 0,
    max_value: raw.max_value ?? 0,
    std_dev: raw.std_dev ?? 0,
    total_readings: raw.total_readings ?? readings.length,
    time_in_range: {
      percentage: raw.time_in_range ?? 0,
      below_range: { percentage: raw.time_below_range ?? 0 },
      above_range: { percentage: raw.time_above_range ?? 0 },
    },
  }
}

function getWindow(timeRange?: string) {
  const now = new Date()
  const days = timeRange ? parseInt(timeRange, 10) : 3
  const start = new Date(now.getTime() - days * 24 * 60 * 60 * 1000)
  return { start, now }
}

export function useGlucose() {
  const [readings, setReadings] = useState<GlucoseReading[]>(demoReadings.slice(0, 72))
  const [stats, setStats] = useState<NormalizedStats>(calculateStats(demoReadings.slice(0, 72)))
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const fetchReadings = useCallback(async (timeRange?: string) => {
    const { start, now } = getWindow(timeRange)
    const params = new URLSearchParams({
      start_time: start.toISOString(),
      end_time: now.toISOString(),
      limit: '400',
    })

    const token = localStorage.getItem('t1d_token')
    const filteredDemo = demoReadings.filter((reading) => new Date(reading.timestamp) >= start)

    if (!token || token.startsWith('demo-')) {
      setReadings(filteredDemo)
      setStats(calculateStats(filteredDemo))
      setDemoMode(true)
      return
    }

    setLoading(true)
    try {
      const readingsResponse = await axios.get(`${API_BASE}/glucose/?${params}`)

      const nextReadings: GlucoseReading[] = Array.isArray(readingsResponse.data)
        ? readingsResponse.data
        : readingsResponse.data?.readings ?? []

      if (nextReadings.length === 0) {
        setReadings(filteredDemo)
        setStats(calculateStats(filteredDemo))
        setDemoMode(true)
        return
      }

      setReadings(nextReadings)
      setStats(calculateStats(nextReadings))
      setDemoMode(false)
    } catch (error) {
      console.info('Using local demo glucose data until the API has records.', error)
      setReadings(filteredDemo)
      setStats(calculateStats(filteredDemo))
      setDemoMode(true)
    } finally {
      setLoading(false)
    }
  }, [])

  const addReading = useCallback(async (data: Omit<GlucoseReading, 'id' | 'timestamp'>) => {
    const payload = {
      ...data,
      timestamp: new Date().toISOString(),
      reading_type: 'sensor',
      source: data.source ?? 'manual',
    }

    try {
      const response = await axios.post(`${API_BASE}/glucose/`, payload)
      setReadings(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch (error) {
      const fallback = { ...payload, id: Date.now(), user_id: 1 } as GlucoseReading
      setReadings(prev => [fallback, ...prev])
      setDemoMode(true)
      return fallback
    }
  }, [])

  const getStats = useCallback(async (timeRange: string) => {
    const { start, now } = getWindow(timeRange)
    const params = new URLSearchParams({ start_time: start.toISOString(), end_time: now.toISOString() })
    try {
      const response = await axios.get(`${API_BASE}/glucose/stats/?${params}`)
      return normalizeStats(response.data, readings)
    } catch (error) {
      return calculateStats(readings)
    }
  }, [readings])

  return { readings, stats, loading, demoMode, fetchReadings, addReading, getStats }
}
