import { useState, useRef, useEffect } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuth } from '../contexts/AuthContext'

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div className="min-h-screen bg-muted/30">
      <header className="sticky top-0 z-50 border-b bg-background">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="font-semibold tracking-tight text-lg" translate="no">SkillHub</Link>
          <div className="flex items-center gap-6">
            {user ? (
              <nav className="flex items-center gap-6">
                <div className="relative" ref={menuRef}>
                  <button
                    className="text-sm transition-colors text-muted-foreground hover:text-foreground"
                    onClick={() => setMenuOpen(!menuOpen)}
                  >
                    {user.username}
                  </button>
                  {menuOpen && (
                    <div className="absolute right-0 top-full mt-1 w-36 rounded-md border bg-white dark:bg-zinc-800 shadow-lg py-1">
                      <Link
                        to="/my"
                        className="block px-3 py-1.5 text-sm text-foreground hover:bg-muted"
                        onClick={() => setMenuOpen(false)}
                      >
                        我的 skills
                      </Link>
                      {user.is_admin && (
                        <Link
                          to="/admin"
                          className="block px-3 py-1.5 text-sm text-foreground hover:bg-muted"
                          onClick={() => setMenuOpen(false)}
                        >
                          用户管理
                        </Link>
                      )}
                      <div className="mx-3 my-1 h-px bg-border" />
                      <button
                        className="w-full px-3 py-1.5 text-left text-sm text-foreground hover:bg-muted"
                        onClick={() => { setMenuOpen(false); logout(); navigate('/') }}
                      >
                        退出
                      </button>
                    </div>
                  )}
                </div>
              </nav>
            ) : (
              <Link to="/login" className="text-sm transition-colors text-muted-foreground hover:text-foreground">登录</Link>
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