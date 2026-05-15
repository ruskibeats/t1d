export interface GlucoseReading {
  id: number
  user_id: number
  glucose_value: number
  timestamp: string
  source?: 'dexcom' | 'nightscout' | 'manual' | 'calibration'
  created_at?: string
  updated_at?: string
}

export interface ContextEvent {
  id: number
  user_id: number
  event_type: 'meal' | 'insulin' | 'exercise' | 'sleep' | 'stress' | 'alcohol' | 'illness' | 'other'
  timestamp: string
  description?: string
  carbs_grams?: number
  protein_grams?: number
  fat_grams?: number
  fiber_grams?: number
  calories?: number
  insulin_units?: number
  insulin_type?: string
  duration?: number
  intensity?: 'low' | 'moderate' | 'high'
  notes?: string
  tags?: string[]
  metadata?: any
  created_at?: string
  updated_at?: string
}

export interface MealEvent extends ContextEvent {
  food_name?: string
  food_category?: string
  glycemic_index?: number
}

export interface InsulinEvent extends ContextEvent {
  bolus_type?: 'rapid' | 'regular' | 'long' | 'ultra_long'
  correction_amount?: number
  carb_ratio?: number
}

export interface ExerciseEvent extends ContextEvent {
  exercise_type?: string
  heart_rate_avg?: number
  heart_rate_max?: number
}

export interface Conversation {
  id: number
  user_id: number
  title: string
  last_message_at: string
  created_at: string
  updated_at: string
}

export interface ConversationMessage {
  id: number
  conversation_id: number
  role: 'user' | 'assistant'
  content: string
  metadata?: any
  created_at: string
}

export interface PatternAnalysis {
  id: number
  user_id: number
  analysis_type: string
  summary: string
  data: any
  confidence_score?: number
  created_at: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface User {
  id: number
  email: string
  first_name?: string
  last_name?: string
  created_at?: string
}

export interface UserCreate {
  email: string
  password: string
  first_name?: string
  last_name?: string
}
