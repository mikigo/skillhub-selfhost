import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'

interface User {
  id: string
  username: string
  status: string
  is_admin: boolean
  created_at: string
}

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  login: (accessToken: string, refreshToken: string, user: User) => void
  logout: () => void
  refreshAuth: () => Promise<boolean>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(() => localStorage.getItem('access_token'))
  const [refreshToken, setRefreshToken] = useState<string | null>(() => localStorage.getItem('refresh_token'))

  const login = useCallback((access: string, refresh: string, u: User) => {
    setAccessToken(access)
    setRefreshToken(refresh)
    setUser(u)
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }, [])

  const logout = useCallback(() => {
    setAccessToken(null)
    setRefreshToken(null)
    setUser(null)
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }, [])

  const refreshAuth = useCallback(async (): Promise<boolean> => {
    if (!refreshToken) return false
    try {
      const resp = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
      if (!resp.ok) {
        logout()
        return false
      }
      const data = await resp.json()
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token)
      localStorage.setItem('access_token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
      return true
    } catch {
      logout()
      return false
    }
  }, [refreshToken, logout])

  useEffect(() => {
    if (accessToken && !user) {
      fetch('/api/auth/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      })
        .then(r => r.ok ? r.json() : null)
        .then(u => {
          if (u) setUser(u)
          else logout()
        })
    }
  }, [accessToken])

  return (
    <AuthContext.Provider value={{ user, accessToken, refreshToken, login, logout, refreshAuth }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}