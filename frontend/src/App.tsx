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

const Placeholder = ({ title }: { title: string }) => (
  <div className="text-center py-20 text-gray-400">{title} - 开发中</div>
)

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
        <Route path="/upload" element={<Upload />} />
        <Route path="/my" element={<MySkills />} />
        <Route path="/admin" element={<Admin />} />
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