/** @jsxImportSource @emotion/react */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'
import { GlucoseReading } from '@/types'

interface GlucoseContextType {
  glucoseReadings: GlucoseReading[]
  stats: any
  loading: boolean
  fetchReadings: (count?: number) => Promise<void>
  addReading: (reading: Omit<GlucoseReading, 'id' | 'timestamp'>) => Promise<void>
}

const GlucoseContext = createContext<GlucoseContextType | undefined>(undefined)

export function GlucoseProvider({ children }: { children: ReactNode }) {
  const [glucoseReadings, setGlucoseReadings] = useState<GlucoseReading[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const fetchReadings = async (count = 50) => {
    setLoading(true)
    try {
      const response = await axios.get(`/api/v1/glucose/recent?count=${count}`)
      setGlucoseReadings(response.data.readings)
      
      if (response.data.stats) {
        setStats(response.data.stats)
      }
    } catch (error) {
      console.error('Failed to fetch glucose readings:', error)
    } finally {
      setLoading(false)
    }
  }

  const addReading = async (reading: Omit<GlucoseReading, 'id' | 'timestamp'>) => {
    try {
      const response = await axios.post('/api/v1/glucose/readings', reading)
      setGlucoseReadings(prev => [response.data, ...prev])
      fetchReadings()
    } catch (error) {
      console.error('Failed to add reading:', error)
      throw error
    }
  }

  useEffect(() => {
    fetchReadings()
  }, [])

  return (
    <GlucoseContext.Provider value={{ glucoseReadings, stats, loading, fetchReadings, addReading }}>
      {children}
    </GlucoseContext.Provider>
  )
}

export function useGlucose() {
  const context = useContext(GlucoseContext)
  if (context === undefined) {
    throw new Error('useGlucose must be used within a GlucoseProvider')
  }
  return context
}
