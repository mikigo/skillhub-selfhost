import { Routes, Route } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { initApiClient } from './api/client'
import { useEffect } from 'react'
import Layout from './components/Layout'

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
        <Route path="/" element={<Placeholder title="首页" />} />
        <Route path="/login" element={<Placeholder title="登录" />} />
        <Route path="/register" element={<Placeholder title="注册" />} />
        <Route path="/skills/:name" element={<Placeholder title="Skill 详情" />} />
        <Route path="/upload" element={<Placeholder title="上传" />} />
        <Route path="/my" element={<Placeholder title="我的" />} />
        <Route path="/admin" element={<Placeholder title="管理" />} />
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