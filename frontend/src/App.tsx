import { Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { initApiClient } from './api/client'
import { useEffect } from 'react'

function AppRoutes() {
  const { accessToken, refreshToken, logout, refreshAuth } = useAuth()

  useEffect(() => {
    initApiClient(
      () => accessToken,
      () => refreshToken,
      refreshAuth,
      logout,
    )
  }, [accessToken, refreshToken, refreshAuth, logout])

  return (
    <Routes>
      <Route path="/" element={<div className="min-h-screen bg-gray-50 flex items-center justify-center"><h1 className="text-2xl font-bold">skillhub</h1></div>} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}