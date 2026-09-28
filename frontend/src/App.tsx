import { Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { initApiClient } from './api/client'
import { useEffect } from 'react'
import Layout from './components/Layout'
import Home from './pages/Home'
import Login from './pages/Login'
import Register from './pages/Register'
import SkillDetail from './pages/SkillDetail'
import MySkills from './pages/MySkills'
import Upload from './pages/Upload'
import Admin from './pages/Admin'
import Author from './pages/Author'
import ProtectedRoute from './components/ProtectedRoute'

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
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/skills/:name" element={<SkillDetail />} />
        <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
        <Route path="/my" element={<ProtectedRoute><MySkills /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute admin><Admin /></ProtectedRoute>} />
        <Route path="/author/:username" element={<Author />} />
      </Route>
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