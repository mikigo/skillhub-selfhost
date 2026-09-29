import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { useT } from '../contexts/I18nContext'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft, Plus, Trash2, ArrowRightLeft } from 'lucide-react'

interface MySkill {
  name: string
  display_name: string
  description: string
  latest_version: string
  tags: string[]
  download_count: number
}

export default function MySkills() {
  const { t } = useT()
  const [skills, setSkills] = useState<MySkill[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadSkills() }, [])

  async function loadSkills() {
    setLoading(true)
    const resp = await apiFetch(`/api/skills/?author=me`)
    const data = await resp.json()
    setSkills(data.items)
    setLoading(false)
  }

  async function handleDelete(name: string) {
    if (!confirm(t('mySkills.deleteConfirm', { name }))) return
    const resp = await apiFetch(`/api/skills/${name}`, { method: 'DELETE' })
    if (resp.ok) {
      toast.success(t('mySkills.deleted'))
      loadSkills()
    } else {
      const data = await resp.json()
      toast.error(data.detail)
    }
  }

  async function handleTransfer(name: string) {
    const target = prompt(t('mySkills.transfer'))
    if (!target) return
    const resp = await apiFetch(`/api/skills/${name}/transfer`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target_user: target }),
    })
    if (resp.ok) {
      toast.success(t('mySkills.transferSuccess'))
      loadSkills()
    } else {
      const data = await resp.json()
      toast.error(data.detail)
    }
  }

  if (loading) return <div className="space-y-4">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-32 w-full" />)}</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4 mr-1" />{t('mySkills.back')}
        </Link>
        <div className="flex items-center gap-3">
          <Link to="/upload"><Button size="sm"><Plus className="h-4 w-4 mr-1" />{t('mySkills.uploadBtn')}</Button></Link>
        </div>
      </div>

      <h2 className="text-lg font-bold mb-4">{t('mySkills.title')} ({skills.length})</h2>

      {skills.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">{t('mySkills.empty')}</div>
      ) : (
        <div className="space-y-3">
          {skills.map(skill => (
            <Card key={skill.name}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <Link to={`/skills/${skill.name}`} className="font-medium hover:text-blue-600">{skill.display_name}</Link>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500" onClick={() => handleDelete(skill.name)} title={t('mySkills.deleteConfirm', { name: skill.name })}>
                      <Trash2 className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleTransfer(skill.name)} title={t('mySkills.transfer')}>
                      <ArrowRightLeft className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="text-sm text-muted-foreground">
                  {skill.latest_version && <span>{skill.latest_version} ({t('mySkills.latest')}) · </span>}
                  {skill.tags.length > 0 && <span>{skill.tags.join(', ')} · </span>}
                  {t('mySkills.totalDownloads')} {skill.download_count.toLocaleString()}
                </div>
                <div className="mt-2 flex gap-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
                <Link to="/upload" className="mt-2 inline-block">
                  <Button variant="outline" size="sm"><Plus className="h-3 w-3 mr-1" />{t('mySkills.addVersion')}</Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}