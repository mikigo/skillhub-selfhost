import { useState, useEffect } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { useT } from '../contexts/I18nContext'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { Skeleton } from '../components/ui/skeleton'
import { ArrowLeft } from 'lucide-react'

interface SkillItem {
  name: string
  display_name: string
  description: string
  latest_version: string
  tags: string[]
  download_count: number
}

export default function Author() {
  const { t } = useT()
  const { username } = useParams<{ username: string }>()
  const [skills, setSkills] = useState<SkillItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadSkills() }, [username])

  async function loadSkills() {
    setLoading(true)
    const resp = await apiFetch(`/api/skills/?author=${encodeURIComponent(username!)}&size=100`)
    const data = await resp.json()
    setSkills(data.items)
    setLoading(false)
  }

  if (loading) return <div className="space-y-3">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-24 w-full" />)}</div>

  return (
    <div>
      <Link to="/" className="flex items-center text-sm text-muted-foreground hover:text-foreground mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />{t('author.back')}
      </Link>

      <h2 className="text-lg font-bold mb-1">{username}</h2>
      <p className="text-sm text-muted-foreground mb-4">{t('author.skillsCount', { count: skills.length })}</p>

      {skills.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">{t('author.noSkills')}</div>
      ) : (
        <div className="space-y-3">
          {skills.map(skill => (
            <Card key={skill.name}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <Link to={`/skills/${skill.name}`} className="font-medium hover:text-blue-600">{skill.display_name}</Link>
                  <span className="text-xs text-muted-foreground">{skill.download_count.toLocaleString()}{t('author.downloads')}</span>
                </div>
                <div className="text-sm text-muted-foreground mb-2">{skill.description}</div>
                <div className="flex gap-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}