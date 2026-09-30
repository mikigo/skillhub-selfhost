import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useT } from '../contexts/I18nContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'

export default function Register() {
  const { t } = useT()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (password !== confirm) {
      toast.error(t('auth.passwordMismatch'))
      return
    }
    setLoading(true)
    try {
      const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!resp.ok) {
        const data = await resp.json()
        throw new Error(data.detail)
      }
      toast.success(t('auth.registerSubmitted'))
      navigate('/')
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex justify-center mt-20">
      <Card className="w-96">
        <CardHeader><CardTitle className="text-center">{t('auth.registerTitle')}</CardTitle></CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <Label htmlFor="username">{t('auth.username')}</Label>
              <Input id="username" name="username" autoComplete="username" spellCheck={false} pattern="[A-Za-z0-9][A-Za-z0-9._\-]*" title={t('auth.usernameHint')} value={username} onChange={e => setUsername(e.target.value)} required />
              <p className="text-xs text-muted-foreground mt-1">{t('auth.usernameHint')}</p>
            </div>
            <div>
              <Label htmlFor="password">{t('auth.password')}</Label>
              <Input id="password" name="password" type="password" autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="confirm">{t('auth.confirmPassword')}</Label>
              <Input id="confirm" name="confirm" type="password" autoComplete="new-password" value={confirm} onChange={e => setConfirm(e.target.value)} required />
            </div>
            <p className="text-xs text-muted-foreground">{t('auth.pendingNote')}</p>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? t('auth.registering') : t('auth.registerBtn')}
            </Button>
          </form>
          <p className="text-sm text-center mt-4">
            {t('auth.hasAccount')}<Link to="/login" className="text-blue-600">{t('auth.loginNow')}</Link>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}