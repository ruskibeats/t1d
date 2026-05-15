/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { ContextEvent } from '@/types'
import { demoEvents } from '@/lib/demoData'

export function useEvents() {
  const [events, setEvents] = useState<ContextEvent[]>(demoEvents)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const fetchEvents = async (limit = 20) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      setEvents(demoEvents)
      setDemoMode(true)
      return
    }

    setLoading(true)
    try {
      const response = await axios.get(`/api/v1/events/?limit=${limit}`)
      const nextEvents = Array.isArray(response.data) ? response.data : response.data?.events ?? []
      setEvents(nextEvents.length > 0 ? nextEvents : demoEvents)
      setDemoMode(nextEvents.length === 0)
    } catch (error) {
      console.info('Using local demo events until the API has records.', error)
      setEvents(demoEvents)
      setDemoMode(true)
    } finally {
      setLoading(false)
    }
  }

  const addEvent = async (event: Omit<ContextEvent, 'id' | 'user_id' | 'timestamp'>) => {
    const payload = { ...event, timestamp: new Date().toISOString() }
    try {
      const response = await axios.post('/api/v1/events/', payload)
      setEvents(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch (error) {
      const fallback = { ...payload, id: Date.now(), user_id: 1 } as ContextEvent
      setEvents(prev => [fallback, ...prev])
      setDemoMode(true)
      return fallback
    }
  }

  useEffect(() => {
    fetchEvents(10)
  }, [])

  return { events, loading, demoMode, fetchEvents, addEvent }
}
