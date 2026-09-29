import { useState, useEffect, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { useT } from '../contexts/I18nContext'
import { Button } from '../components/ui/button'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, Copy, Download, Trash2 } from 'lucide-react'

interface Version {
  version: string
  release_notes: string | null
  file_size: number
  created_at: string
}

interface SkillDetail {
  name: string
  display_name: string
  description: string
  author: { username: string; status: string }
  original_author: string | null
  source_url: string | null
  tags: string[]
  download_count: number
  versions: Version[]
}

function splitFrontmatter(md: string): { frontmatter: string; body: string } {
  const trimmed = md.trimStart()
  if (!trimmed.startsWith('---')) return { frontmatter: '', body: md }
  const end = trimmed.indexOf('\n---', 3)
  if (end === -1) return { frontmatter: '', body: md }
  return {
    frontmatter: trimmed.slice(3, end).trim(),
    body: trimmed.slice(end + 4).trimStart(),
  }
}

export default function SkillDetail() {
  const { name } = useParams<{ name: string }>()
  const { user } = useAuth()
  const { t } = useT()
  const [skill, setSkill] = useState<SkillDetail | null>(null)
  const [readme, setReadme] = useState('')
  const [selectedVersion, setSelectedVersion] = useState('')
  const [loading, setLoading] = useState(true)
  const isAuthor = user?.username === skill?.author?.username

  useEffect(() => { loadSkill() }, [name])

  async function loadSkill(version?: string) {
    setLoading(true)
    const query = version ? `?version=${version}` : ''
    const resp = await apiFetch(`/api/skills/${name}${query}`)
    if (!resp.ok) { setLoading(false); return }
    const data = await resp.json()
    setSkill(data)
    const v = version || data.versions[0]?.version
    setSelectedVersion(v)

    if (v) {
      const rmResp = await apiFetch(`/api/skills/${name}/readme?version=${v}`)
      if (rmResp.ok) setReadme(await rmResp.text())
    }

    setLoading(false)
  }

  function handleVersionClick(version: string) {
    setSelectedVersion(version)
    loadSkill(version)
  }

  async function handleDeleteVersion(version: string) {
    if (!confirm(t('skillDetail.deleteConfirm', { version }))) return
    const resp = await apiFetch(`/api/skills/${name}/versions/${version}`, { method: 'DELETE' })
    if (resp.ok) { toast.success(t('skillDetail.deleted')); loadSkill() }
    else { const data = await resp.json(); toast.error(data.detail) }
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  const { frontmatter, body } = useMemo(() => splitFrontmatter(readme), [readme])

  const downloadUrl = `api/skills/${name}/download${selectedVersion ? `?version=${selectedVersion}` : ''}`
  const fullUrl = `${window.location.origin}/${downloadUrl}`
  const cmdUnix = `curl -sSL -o /tmp/skill.zip ${fullUrl} && unzip -o /tmp/skill.zip -d ~/.agent/skills/`
  const cmdWin = `Invoke-WebRequest -Uri "${fullUrl}" -OutFile "$env:TEMP\\skill.zip"; Expand-Archive -Path "$env:TEMP\\skill.zip" -DestinationPath "$env:USERPROFILE\\.agent\\skills" -Force`

  const copyToClipboard = (text: string) => { navigator.clipboard.writeText(text); toast.success(t('skillDetail.copied')) }

  if (loading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-96 w-full" /></div>
  if (!skill) return <div className="text-center py-20 text-muted-foreground">{t('skillDetail.notFound')}</div>

  return (
    <div>
      <div className="mb-4">
        <Link to="/" className="flex items-center text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4 mr-1" />{t('skillDetail.back')}
        </Link>
      </div>

      <h1 className="text-2xl font-bold mb-4">{skill.display_name}</h1>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-9">
          <Card>
            <CardContent className="p-6">
              {frontmatter && (
                <pre className="text-xs text-muted-foreground font-mono bg-muted dark:bg-zinc-800/50 rounded p-3 mb-4 overflow-x-auto border whitespace-pre-wrap break-words">
                  {frontmatter}
                </pre>
              )}
              <div className="md-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => <h1 className="text-2xl font-bold mb-3 mt-6 first:mt-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-xl font-bold mb-2 mt-5">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 mt-4">{children}</h3>,
                    p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                    li: ({ children }) => <li className="mb-1">{children}</li>,
                    table: ({ children }) => <div className="overflow-x-auto mb-3"><table className="w-full border-collapse border border-gray-200 text-sm">{children}</table></div>,
                    thead: ({ children }) => <thead className="bg-muted dark:bg-zinc-800/50">{children}</thead>,
                    tbody: ({ children }) => <tbody>{children}</tbody>,
                    tr: ({ children }) => <tr className="border-b border-gray-200">{children}</tr>,
                    th: ({ children }) => <th className="px-3 py-2 text-left font-medium text-muted-foreground">{children}</th>,
                    td: ({ children }) => <td className="px-3 py-2">{children}</td>,
                    code: ({ children, className, ...props }: any) => {
                      const isInline = !className
                      return isInline
                        ? <code className="bg-muted rounded px-1 py-0.5 text-sm font-mono" {...props}>{children}</code>
                        : <code className="block bg-gray-900 text-gray-100 rounded p-3 text-sm font-mono overflow-x-auto mb-3 whitespace-pre-wrap break-words" {...props}>{children}</code>
                    },
                    pre: ({ children }) => <pre className="mb-3">{children}</pre>,
                    blockquote: ({ children }) => <blockquote className="border-l-4 border-border pl-4 italic text-muted-foreground mb-3">{children}</blockquote>,
                    a: ({ children, href }) => <a href={href} className="text-blue-600 underline" target="_blank" rel="noopener">{children}</a>,
                    hr: () => <hr className="my-4" />,
                    strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                  }}
                >
                  {body || `# ${t('skillDetail.noReadme')}`}
                </ReactMarkdown>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="col-span-3 space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div>
                <div className="text-sm text-muted-foreground mb-2">{t('skillDetail.install')}</div>
                <div className="space-y-2">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">{t('skillDetail.macLinux')}</span>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => copyToClipboard(cmdUnix)}>
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="bg-muted rounded p-2 text-xs font-mono break-all">{cmdUnix}</div>
                  </div>
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">{t('skillDetail.windowsPS')}</span>
                      <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => copyToClipboard(cmdWin)}>
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="bg-muted rounded p-2 text-xs font-mono break-all">{cmdWin}</div>
                  </div>
                </div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">{t('skillDetail.basicInfo')}</div>
                <div className="text-sm mt-1">{t('skillDetail.author')}: <Link to={`/author/${skill.author.username}`} className="text-blue-600 hover:underline">{skill.author.username}</Link></div>
                {skill.original_author && <div className="text-sm text-muted-foreground">原作者: {skill.original_author}</div>}
                {skill.source_url && <div className="text-sm text-muted-foreground truncate">来源: <a href={skill.source_url} className="text-blue-600 hover:underline" target="_blank" rel="noopener">{skill.source_url}</a></div>}
                <div className="text-sm">{t('skillDetail.downloads')}: {skill.download_count.toLocaleString()}</div>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-sm text-muted-foreground mb-2">{t('skillDetail.versions')}</div>
              <div className="space-y-1">
                {skill.versions.map((v) => (
                  <div
                    key={v.version}
                    className={`flex items-center justify-between p-2 rounded text-sm cursor-pointer ${selectedVersion === v.version ? 'bg-primary/10 dark:bg-primary/20' : 'hover:bg-muted dark:bg-zinc-800/50'}`}
                    onClick={() => handleVersionClick(v.version)}
                  >
                    <div>
                      <span className={selectedVersion === v.version ? 'font-medium text-blue-600' : ''}>{v.version}</span>
                      {skill.versions[0]?.version === v.version && <Badge variant="outline" className="ml-1 text-[10px]">{t('skillDetail.latest')}</Badge>}
                      <div className="text-xs text-muted-foreground">{formatSize(v.file_size)}</div>
                    </div>
                    <div className="flex gap-1">
                      <a href={`api/skills/${name}/download?version=${v.version}`} onClick={e => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-7 w-7"><Download className="h-3 w-3" /></Button>
                      </a>
                      {isAuthor && (
                        <Button variant="ghost" size="icon" className="h-7 w-7 text-red-500" onClick={(e) => { e.stopPropagation(); handleDeleteVersion(v.version) }}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}