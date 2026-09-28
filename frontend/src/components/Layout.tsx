import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { Button } from './ui/button'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b bg-white">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-bold text-lg">SkillHub</Link>
          <div className="flex items-center gap-3">
            {user ? (
              <>
                <span className="text-sm text-gray-600">{user.username}</span>
                {user.is_admin && <Link to="/admin" className="text-sm text-blue-600">管理</Link>}
                <Link to="/my" className="text-sm text-gray-600">我的</Link>
                <Button variant="ghost" size="sm" onClick={() => { logout(); navigate('/') }}>退出</Button>
              </>
            ) : (
              <Link to="/login"><Button variant="ghost" size="sm">登录</Button></Link>
            )}
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6">
        <Outlet />
      </main>
      <Toaster position="top-right" />
    </div>
  )
}