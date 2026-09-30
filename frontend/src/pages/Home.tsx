import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { skillPath } from '@/lib/skillPath'
import { Input } from '../components/ui/input'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { useT } from '../contexts/I18nContext'
import { Search, ChevronLeft, ChevronRight } from 'lucide-react'

interface SkillItem {
  name: string
  display_name: string
  description: string
  author: { username: string; status: string }
  original_author: string | null
  source_url: string | null
  latest_version: string
  tags: string[]
  download_count: number
}

export default function Home() {
  const { t } = useT()
  const [skills, setSkills] = useState<SkillItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const [activeTags, setActiveTags] = useState<string[]>([])
  const [sort, setSort] = useState('downloads')
  const [loading, setLoading] = useState(true)
  const [allTags, setAllTags] = useState<string[]>([])

  const PAGE_SIZE = 20

  useEffect(() => {
    loadSkills()
  }, [page, activeTags, sort])

  async function loadSkills() {
    setLoading(true)
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('size', String(PAGE_SIZE))
    params.set('sort', sort)
    if (q) params.set('q', q)
    activeTags.forEach(t => params.append('tag', t))

    const resp = await apiFetch(`/api/skills/?${params}`)
    const data = await resp.json()
    setSkills(data.items)
    setTotal(data.total)

    if (allTags.length === 0 && data.items.length > 0) {
      const tags = new Set<string>()
      data.items.forEach((s: SkillItem) => s.tags.forEach(t => tags.add(t)))
      setAllTags(Array.from(tags).sort())
    }
    setLoading(false)
  }

  function toggleTag(tag: string) {
    setActiveTags(prev => prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag])
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    setPage(1)
    loadSkills()
  }

  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div>
      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-10"
            name="q"
            autoComplete="off"
            spellCheck={false}
            placeholder={t('home.search')}
            value={q}
            onChange={e => setQ(e.target.value)}
          />
        </div>
      </form>

      <div className="flex gap-6 mb-4">
        {([
          { key: 'downloads' as const, count: total },
          { key: 'weekly' as const },
          { key: 'newest' as const },
        ]).map((item) => (
          <button
            key={item.key}
            className={`pb-1.5 text-sm font-medium border-b-2 transition-colors ${sort === item.key ? 'border-foreground text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
            onClick={() => { setSort(item.key); setPage(1) }}
          >
            {t(`home.${item.key}`)}
            {'count' in item && <span className="ml-1 text-muted-foreground">({(item as any).count.toLocaleString()})</span>}
          </button>
        ))}
      </div>

      {allTags.length > 0 && (
        <div className="flex gap-1 mb-4 flex-wrap">
          <Badge variant={activeTags.length === 0 ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setActiveTags([])}>
            All
          </Badge>
          {allTags.map(tag => (
            <Badge key={tag} variant={activeTags.includes(tag) ? 'default' : 'outline'} className="cursor-pointer" onClick={() => toggleTag(tag)}>
              {tag}
            </Badge>
          ))}
        </div>
      )}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16 w-full" />)}
        </div>
      ) : skills.length === 0 ? (
        <div className="text-center py-20 text-muted-foreground">{t('home.empty')}</div>
      ) : (
        <div className="space-y-2">
          <div className="grid gap-3 text-xs text-muted-foreground px-3 py-2 border-b" style={{ gridTemplateColumns: '1fr 15fr 3fr' }}>
            <span>{t('home.headerNum')}</span>
            <span>{t('home.headerSkill')}</span>
            <span className="text-right">{t('home.headerDownloads')}</span>
          </div>
          {skills.map((skill, i) => (
            <Link
              key={`${skill.author.username}/${skill.name}`}
              to={skillPath(skill.author.username, skill.name)}
              className="grid gap-3 px-3 py-2 rounded hover:bg-muted items-center"
              style={{ gridTemplateColumns: '1fr 15fr 3fr' }}
            >
              <span className="text-sm text-muted-foreground">{(page - 1) * PAGE_SIZE + i + 1}</span>
              <div className="min-w-0" title={skill.description}>
                <div className="font-medium truncate">
                  {skill.display_name}
                  <span className="ml-2 text-xs text-muted-foreground font-normal">
                    {skill.author.username}{skill.original_author ? `[${skill.original_author}]` : ''}
                  </span>
                </div>
                <div className="text-xs text-muted-foreground truncate">{skill.description}</div>
              </div>
              <span className="text-sm text-right text-muted-foreground">{skill.download_count.toLocaleString()}</span>
            </Link>
          ))}
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex justify-center items-center gap-2 mt-4">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="text-sm">{page} / {totalPages}</span>
          <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      )}
    </div>
  )
}