import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { GlucosePage } from './pages/Glucose'
import { EventsPage } from './pages/Events'
import { PatternsPage } from './pages/Patterns'
import { ChatPage } from './pages/Chat'
import { SettingsPage } from './pages/Settings'
import { LoginPage } from './pages/Login'
import { SleepLogPage } from './pages/SleepLog'
import { HealthMetricsPage } from './pages/HealthMetrics'
import { FoodLogPage } from './pages/FoodLog'
import { ExerciseLogPage } from './pages/ExerciseLog'
import './App.css'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
            <div className="App min-h-screen">
              <Toaster position="top-right" />
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route element={<Layout />}>
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<Dashboard />} />
                  <Route path="/glucose" element={<GlucosePage />} />
                  <Route path="/events" element={<EventsPage />} />
                  <Route path="/patterns" element={<PatternsPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                  <Route path="/sleep" element={<SleepLogPage />} />
                  <Route path="/health-metrics" element={<HealthMetricsPage />} />
                  <Route path="/food" element={<FoodLogPage />} />
                  <Route path="/exercise" element={<ExerciseLogPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                </Route>
              </Routes>
            </div>
          </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
