import { useState, useRef, useEffect, useCallback } from 'react'
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useTheme } from 'next-themes'
import { useAuth } from '../contexts/AuthContext'
import { useT } from '../contexts/I18nContext'
import { Sun, Moon, Check, ChevronDown } from 'lucide-react'

type Lang = 'zh' | 'en'

const LANGUAGES: { key: Lang; label: string }[] = [
  { key: 'en', label: 'English' },
  { key: 'zh', label: '简体中文' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const { t, lang, setLang } = useT()
  const navigate = useNavigate()
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const [langMenuOpen, setLangMenuOpen] = useState(false)
  const langMenuRef = useRef<HTMLDivElement>(null)
  const [headerVisible, setHeaderVisible] = useState(true)
  const [siteConfig, setSiteConfig] = useState<{ logo_text: string; logo: string }>({ logo_text: 'SkillHub', logo: '' })
  const lastScrollY = useRef(0)

  useEffect(() => {
    fetch('/api/config').then(r => r.json()).then(c => setSiteConfig(c)).catch(() => {})
  }, [])

  const handleScroll = useCallback(() => {
    const current = window.scrollY
    if (current < 60) {
      setHeaderVisible(true)
    } else if (current > lastScrollY.current + 5) {
      setHeaderVisible(false)
    } else if (current < lastScrollY.current - 5) {
      setHeaderVisible(true)
    }
    lastScrollY.current = current
  }, [])

  useEffect(() => {
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [handleScroll])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
      if (langMenuRef.current && !langMenuRef.current.contains(e.target as Node)) {
        setLangMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950">
      <header className={`sticky top-0 z-50 border-b bg-white dark:bg-zinc-900 transition-transform duration-300 ${headerVisible ? 'translate-y-0' : '-translate-y-full'}`}>
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight text-lg" translate="no">
            {siteConfig.logo && <img src="/api/config/logo" alt="" width="24" height="24" className="h-6 w-6 object-contain" />}
            <span>{siteConfig.logo_text}</span>
          </Link>
          <div className="flex items-center">
            <button
              aria-label={t('app.themeToggle')}
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
            >
              <Sun className="h-4 w-4 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" aria-hidden="true" />
              <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" aria-hidden="true" />
            </button>
            <div className="relative mx-3" ref={langMenuRef}>
              <button
                className="inline-flex h-9 shrink-0 items-center gap-1 rounded-md px-2 text-sm transition-colors text-muted-foreground hover:bg-muted hover:text-foreground"
                onClick={() => setLangMenuOpen(!langMenuOpen)}
              >
                {LANGUAGES.find(l => l.key === lang)?.label ?? 'English'}
                <ChevronDown className={`h-3.5 w-3.5 transition-transform ${langMenuOpen ? 'rotate-180' : ''}`} />
              </button>
              {langMenuOpen && (
                <div className="absolute right-0 top-full mt-1 w-36 rounded-md border bg-white dark:bg-zinc-800 shadow-lg py-1">
                  {LANGUAGES.map(l => (
                    <button
                      key={l.key}
                      className="w-full flex items-center justify-between px-3 py-1.5 text-sm text-foreground hover:bg-muted"
                      onClick={() => { setLang(l.key); setLangMenuOpen(false) }}
                    >
                      {l.label}
                      {lang === l.key && <Check className="h-3.5 w-3.5" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {user ? (
              <div className="relative" ref={userMenuRef}>
                <button
                  className="inline-flex h-9 shrink-0 min-w-[80px] items-center justify-center rounded-md px-3 text-sm transition-colors text-muted-foreground hover:bg-muted hover:text-foreground"
                  onClick={() => setUserMenuOpen(!userMenuOpen)}
                >
                  {user.username}
                </button>
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-36 rounded-md border bg-white dark:bg-zinc-800 shadow-lg py-1">
                    <Link
                      to="/my"
                      className="block px-3 py-1.5 text-sm text-foreground hover:bg-muted"
                      onClick={() => setUserMenuOpen(false)}
                    >
                      {t('nav.mySkills')}
                    </Link>
                    {user.is_admin && (
                      <Link
                        to="/admin"
                        className="block px-3 py-1.5 text-sm text-foreground hover:bg-muted"
                        onClick={() => setUserMenuOpen(false)}
                      >
                        {t('nav.admin')}
                      </Link>
                    )}
                    <div className="mx-3 my-1 h-px bg-border" />
                    <button
                      className="w-full px-3 py-1.5 text-left text-sm text-foreground hover:bg-muted"
                      onClick={() => { setUserMenuOpen(false); logout(); navigate('/') }}
                    >
                      {t('app.logout')}
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link to="/login" className="inline-flex h-9 shrink-0 min-w-[80px] items-center justify-center rounded-md px-3 text-sm transition-colors text-muted-foreground hover:bg-muted hover:text-foreground">{t('app.login')}</Link>
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