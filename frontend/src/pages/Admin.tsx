import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { useT } from '../contexts/I18nContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Card, CardContent } from '../components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import { Badge } from '../components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog'
import { Skeleton } from '../components/ui/skeleton'
import { Plus } from 'lucide-react'

interface UserItem {
  id: string
  username: string
  status: string
  is_admin: boolean
  created_at: string
}

export default function Admin() {
  const { t } = useT()
  const [users, setUsers] = useState<UserItem[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')

  useEffect(() => { loadUsers() }, [])

  async function loadUsers(status?: string) {
    setLoading(true)
    const params = status ? `?status=${status}` : ''
    const resp = await apiFetch(`/api/admin/users/${params}`)
    const data = await resp.json()
    setUsers(data.items)
    setLoading(false)
  }

  async function approveUser(id: string) {
    const resp = await apiFetch(`/api/admin/users/${id}/approve`, { method: 'PATCH' })
    if (resp.ok) { toast.success(t('admin.approved')); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function disableUser(id: string) {
    if (!confirm(t('admin.disableConfirm'))) return
    const resp = await apiFetch(`/api/admin/users/${id}/disable`, { method: 'PATCH' })
    if (resp.ok) { toast.success(t('admin.disabledMsg')); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function enableUser(id: string) {
    const resp = await apiFetch(`/api/admin/users/${id}/enable`, { method: 'PATCH' })
    if (resp.ok) { toast.success(t('admin.enabled')); loadUsers() }
    else { const d = await resp.json(); toast.error(d.detail) }
  }

  async function createUser(e: React.FormEvent) {
    e.preventDefault()
    const resp = await apiFetch('/api/admin/users/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: newUsername, password: newPassword }),
    })
    if (resp.ok) {
      toast.success(t('admin.userCreated'))
      setCreateOpen(false)
      setNewUsername('')
      setNewPassword('')
      loadUsers()
    } else {
      const d = await resp.json()
      toast.error(d.detail)
    }
  }

  const statusIcon = (s: string) => {
    if (s === 'active') return <span className="text-green-500">{t('admin.active')}</span>
    if (s === 'pending') return <span className="text-yellow-500">{t('admin.pendingStatus')}</span>
    return <span className="text-red-500">{t('admin.disabled')}</span>
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">{t('admin.title')}</h2>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button size="sm"><Plus className="h-4 w-4 mr-1" />{t('admin.createUser')}</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>{t('admin.createTitle')}</DialogTitle></DialogHeader>
            <form onSubmit={createUser} className="space-y-3">
              <div><Label>{t('auth.username')}</Label><Input name="username" autoComplete="username" spellCheck={false} value={newUsername} onChange={e => setNewUsername(e.target.value)} required /></div>
              <div><Label>{t('auth.password')}</Label><Input name="password" type="password" autoComplete="new-password" value={newPassword} onChange={e => setNewPassword(e.target.value)} required /></div>
              <Button type="submit">{t('admin.createUser')}</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <Tabs defaultValue="all" onValueChange={v => loadUsers(v === 'all' ? undefined : v)}>
        <TabsList>
          <TabsTrigger value="all">{t('admin.allUsers')}</TabsTrigger>
          <TabsTrigger value="pending">{t('admin.pending')}</TabsTrigger>
        </TabsList>
        <TabsContent value="all" className="mt-4">
          {loading ? <Skeleton className="h-64 w-full" /> : users.length === 0 ? (
            <div className="text-center py-10 text-muted-foreground">{t('admin.noUsers')}</div>
          ) : (
            <div className="space-y-2">
              {users.map(u => (
                <Card key={u.id}>
                  <CardContent className="p-3 flex items-center justify-between">
                    <div>
                      <span className="font-medium">{u.username}</span>
                      {u.is_admin && <Badge variant="default" className="ml-2">{t('admin.adminBadge')}</Badge>}
                      <span className="ml-2 text-sm">{statusIcon(u.status)}</span>
                      <span className="ml-2 text-xs text-muted-foreground">{new Date(u.created_at).toLocaleDateString()}</span>
                    </div>
                    <div className="flex gap-1">
                      {u.status === 'pending' && (
                        <>
                          <Button variant="outline" size="sm" onClick={() => approveUser(u.id)}>{t('admin.approve')}</Button>
                          <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>{t('admin.reject')}</Button>
                        </>
                      )}
                      {u.status === 'active' && !u.is_admin && (
                        <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>{t('admin.disable')}</Button>
                      )}
                      {u.status === 'disabled' && (
                        <Button variant="outline" size="sm" onClick={() => enableUser(u.id)}>{t('admin.enable')}</Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
        <TabsContent value="pending">
          {loading ? <Skeleton className="h-64 w-full" /> : users.length === 0 ? (
            <div className="text-center py-10 text-muted-foreground">{t('admin.noPending')}</div>
          ) : (
            <div className="space-y-2 mt-4">
              {users.map(u => (
                <Card key={u.id}>
                  <CardContent className="p-3 flex items-center justify-between">
                    <div><span className="font-medium">{u.username}</span><span className="ml-2 text-xs text-muted-foreground">{new Date(u.created_at).toLocaleDateString()}</span></div>
                    <div className="flex gap-1">
                      <Button variant="outline" size="sm" onClick={() => approveUser(u.id)}>{t('admin.approve')}</Button>
                      <Button variant="outline" size="sm" onClick={() => disableUser(u.id)}>{t('admin.reject')}</Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}