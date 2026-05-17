/** @jsxImportSource @emotion/react */
import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import axios from 'axios'

interface User {
  id: number
  email: string
  first_name?: string
  last_name?: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

const demoUser = { id: 1, email: 'demo@t1d.com', first_name: 'Demo', last_name: 'User' }

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    const storedToken = localStorage.getItem('t1d_token')
    const storedUser = localStorage.getItem('t1d_user')
    if (storedToken) {
      setToken(storedToken)
      if (!storedToken.startsWith('demo-')) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${storedToken}`
      }
    }
    if (storedUser) {
      setUser(JSON.parse(storedUser))
    }
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const params = new URLSearchParams()
      params.append('username', email)
      params.append('password', password)
      const response = await axios.post('/auth/login', params, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      const { access_token, user: userData } = response.data
      const nextUser = userData ?? { id: 1, email, first_name: '', last_name: '' }

      localStorage.setItem('t1d_token', access_token)
      localStorage.setItem('t1d_user', JSON.stringify(nextUser))
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`

      setToken(access_token)
      setUser(nextUser)
    } catch (error) {
      if (email === 'demo@t1d.com' && password === 'demo123') {
        const demoToken = `demo-${Date.now()}`
        localStorage.setItem('t1d_token', demoToken)
        localStorage.setItem('t1d_user', JSON.stringify(demoUser))
        delete axios.defaults.headers.common['Authorization']
        setToken(demoToken)
        setUser(demoUser)
        return
      }
      throw error
    }
  }

  const logout = () => {
    localStorage.removeItem('t1d_token')
    localStorage.removeItem('t1d_user')
    delete axios.defaults.headers.common['Authorization']
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
