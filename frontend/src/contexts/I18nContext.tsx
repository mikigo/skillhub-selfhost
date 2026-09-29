import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { zh, en } from '../i18n/translations'

type Lang = 'zh' | 'en'
type Translations = typeof zh

function getNested(obj: any, path: string): string {
  return path.split('.').reduce((o, k) => o?.[k], obj) ?? path
}

interface I18nState {
  lang: Lang
  t: (key: string, vars?: Record<string, string | number>) => string
  setLang: (l: Lang) => void
}

const I18nContext = createContext<I18nState | null>(null)

const dict: Record<Lang, Translations> = { zh, en }

const STORAGE_KEY = 'skillhub_lang'

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored === 'zh' || stored === 'en') return stored
    } catch {}
    return 'en'
  })

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY)) return
    fetch('/api/config')
      .then(r => r.json())
      .then(c => {
        if (c.default_lang === 'zh' || c.default_lang === 'en') {
          setLangState(c.default_lang)
          try { localStorage.setItem(STORAGE_KEY, c.default_lang) } catch {}
        }
      })
      .catch(() => {})
  }, [])

  const setLang = useCallback((l: Lang) => {
    setLangState(l)
    try { localStorage.setItem(STORAGE_KEY, l) } catch {}
  }, [])

  const t = useCallback((key: string, vars?: Record<string, string | number>) => {
    let val = getNested(dict[lang], key)
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        val = val.replace(`{${k}}`, String(v))
      }
    }
    return val
  }, [lang])

  return (
    <I18nContext.Provider value={{ lang, t, setLang }}>
      {children}
    </I18nContext.Provider>
  )
}

export function useT() {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useT must be used within I18nProvider')
  return ctx
}