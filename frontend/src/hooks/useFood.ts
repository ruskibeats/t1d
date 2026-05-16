/** @jsxImportSource @emotion/react */
import { useState, useEffect } from 'react'
import axios from 'axios'

export interface FoodItem {
  id: number
  name: string
  brand_name?: string
  serving_size?: number
  serving_unit?: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
  fiber?: number
  sugars?: number
  source: string
}

export interface FoodEntry {
  id: number
  food_id?: number
  quantity: number
  unit: string
  entry_date: string
  meal_type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  food_name?: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
  fiber?: number
  sugars?: number
}

const demoFoods: FoodItem[] = [
  { id: 1, name: 'Banana', serving_size: 1, serving_unit: 'medium', calories: 105, protein: 1.3, carbs: 27, fat: 0.4, source: 'demo' },
  { id: 2, name: 'Oatmeal', brand_name: 'Quaker', serving_size: 40, serving_unit: 'g', calories: 150, protein: 5, carbs: 27, fat: 2.5, source: 'demo' },
  { id: 3, name: 'Chicken Breast', serving_size: 100, serving_unit: 'g', calories: 165, protein: 31, carbs: 0, fat: 3.6, source: 'demo' },
  { id: 4, name: 'Brown Rice', serving_size: 1, serving_unit: 'cup', calories: 216, protein: 5, carbs: 45, fat: 1.8, source: 'demo' },
  { id: 5, name: 'Greek Yogurt', brand_name: 'Fage', serving_size: 200, serving_unit: 'g', calories: 146, protein: 20, carbs: 8, fat: 3.8, source: 'demo' },
]

const demoEntries: FoodEntry[] = [
  { id: 1, food_name: 'Oatmeal', quantity: 1, unit: 'serving', entry_date: new Date().toISOString(), meal_type: 'breakfast', calories: 150, protein: 5, carbs: 27, fat: 2.5 },
  { id: 2, food_name: 'Banana', quantity: 1, unit: 'medium', entry_date: new Date().toISOString(), meal_type: 'breakfast', calories: 105, protein: 1.3, carbs: 27, fat: 0.4 },
  { id: 3, food_name: 'Chicken Breast', quantity: 1, unit: 'serving', entry_date: new Date().toISOString(), meal_type: 'lunch', calories: 165, protein: 31, carbs: 0, fat: 3.6 },
  { id: 4, food_name: 'Brown Rice', quantity: 1, unit: 'cup', entry_date: new Date().toISOString(), meal_type: 'lunch', calories: 216, protein: 5, carbs: 45, fat: 1.8 },
  { id: 5, food_name: 'Greek Yogurt', quantity: 1, unit: 'serving', entry_date: new Date().toISOString(), meal_type: 'snack', calories: 146, protein: 20, carbs: 8, fat: 3.8 },
]

export function useFood() {
  const [foods, setFoods] = useState<FoodItem[]>([])
  const [entries, setEntries] = useState<FoodEntry[]>(demoEntries)
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(false)
  const [demoMode, setDemoMode] = useState(true)

  const searchFoods = async (query: string) => {
    if (!query.trim()) {
      setFoods([])
      return
    }

    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      const q = query.toLowerCase()
      setFoods(demoFoods.filter(f => f.name.toLowerCase().includes(q)))
      setDemoMode(true)
      return
    }

    setSearching(true)
    try {
      const response = await axios.get(`/api/v1/food/search?q=${encodeURIComponent(query)}`)
      const results = Array.isArray(response.data) ? response.data : []
      setFoods(results.length > 0 ? results : demoFoods.filter(f => f.name.toLowerCase().includes(query.toLowerCase())))
      setDemoMode(results.length === 0)
    } catch (error) {
      console.info('Using demo foods for search.', error)
      setFoods(demoFoods.filter(f => f.name.toLowerCase().includes(query.toLowerCase())))
      setDemoMode(true)
    } finally {
      setSearching(false)
    }
  }

  const createEntry = async (data: Omit<FoodEntry, 'id'>) => {
    try {
      const response = await axios.post('/api/v1/food/entries', data)
      setEntries(prev => [response.data, ...prev])
      setDemoMode(false)
      return response.data
    } catch (error) {
      const fallback: FoodEntry = { ...data, id: Date.now() }
      setEntries(prev => [fallback, ...prev])
      setDemoMode(true)
      return fallback
    }
  }

  const listEntries = async (start?: string, end?: string) => {
    const token = localStorage.getItem('t1d_token')
    if (!token || token.startsWith('demo-')) {
      setEntries(demoEntries)
      setDemoMode(true)
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const response = await axios.get(`/api/v1/food/entries?${params.toString()}`)
      const nextEntries = Array.isArray(response.data) ? response.data : []
      setEntries(nextEntries.length > 0 ? nextEntries : demoEntries)
      setDemoMode(nextEntries.length === 0)
    } catch (error) {
      console.info('Using demo food entries.', error)
      setEntries(demoEntries)
      setDemoMode(true)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    listEntries()
  }, [])

  return { foods, entries, searching, loading, demoMode, searchFoods, createEntry, listEntries }
}
