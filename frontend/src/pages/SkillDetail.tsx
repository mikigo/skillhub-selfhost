import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
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
  tags: string[]
  download_count: number
  versions: Version[]
}

export default function SkillDetail() {
  const { name } = useParams<{ name: string }>()
  const { user } = useAuth()
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
    if (!confirm(`确定删除版本 ${version}？`)) return
    const resp = await apiFetch(`/api/skills/${name}/versions/${version}`, { method: 'DELETE' })
    if (resp.ok) { toast.success('版本已删除'); loadSkill() }
    else { const data = await resp.json(); toast.error(data.detail) }
  }

  function formatSize(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1048576).toFixed(1)} MB`
  }

  const downloadUrl = `api/skills/${name}/download${selectedVersion ? `?version=${selectedVersion}` : ''}`
  const cmd = `curl -o ${name}-v${selectedVersion}.zip ${window.location.origin}/${downloadUrl}`

  if (loading) return <div className="space-y-4"><Skeleton className="h-8 w-64" /><Skeleton className="h-96 w-full" /></div>
  if (!skill) return <div className="text-center py-20 text-gray-400">skill 不存在</div>

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <Link to="/" className="flex items-center text-sm text-gray-500 hover:text-gray-700">
          <ArrowLeft className="h-4 w-4 mr-1" />返回
        </Link>
        <span className="text-sm text-gray-500">{skill.display_name} @ {selectedVersion}</span>
      </div>

      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-9">
          <Card>
            <CardContent className="p-6 md-p">
              <ReactMarkdown
                components={{
                  h1: ({ children }) => <h1 className="text-2xl font-bold mb-3 mt-6 first:mt-0">{children}</h1>,
                  h2: ({ children }) => <h2 className="text-xl font-bold mb-2 mt-5">{children}</h2>,
                  h3: ({ children }) => <h3 className="text-lg font-semibold mb-2 mt-4">{children}</h3>,
                  p: ({ children }) => <p className="mb-3 leading-relaxed">{children}</p>,
                  ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1">{children}</ul>,
                  ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1">{children}</ol>,
                  li: ({ children }) => <li className="mb-1">{children}</li>,
                  code: ({ children, className, ...props }: any) => {
                    const isInline = !className
                    return isInline
                      ? <code className="bg-gray-100 rounded px-1 py-0.5 text-sm font-mono" {...props}>{children}</code>
                      : <code className="block bg-gray-900 text-gray-100 rounded p-3 text-sm font-mono overflow-x-auto mb-3" {...props}>{children}</code>
                  },
                  pre: ({ children }) => <pre className="mb-3">{children}</pre>,
                  blockquote: ({ children }) => <blockquote className="border-l-4 border-gray-300 pl-4 italic text-gray-600 mb-3">{children}</blockquote>,
                  a: ({ children, href }) => <a href={href} className="text-blue-600 underline" target="_blank" rel="noopener">{children}</a>,
                  hr: () => <hr className="my-4" />,
                  strong: ({ children }) => <strong className="font-bold">{children}</strong>,
                }}
              >
                {readme || '# 暂无 README'}
              </ReactMarkdown>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardContent className="p-4 space-y-3">
              <div>
                <div className="text-sm text-gray-500 mb-1">安装命令</div>
                <div className="bg-gray-100 rounded p-2 text-xs font-mono break-all">{cmd}</div>
                <Button variant="ghost" size="sm" className="mt-1" onClick={() => { navigator.clipboard.writeText(cmd); toast.success('已复制') }}>
                  <Copy className="h-3 w-3 mr-1" />复制
                </Button>
              </div>
              <div>
                <div className="text-sm text-gray-500">基本信息</div>
                <div className="text-sm mt-1">作者: {skill.author.username}</div>
                <div className="text-sm">下载: {skill.download_count.toLocaleString()} 次</div>
                <div className="flex gap-1 mt-1 flex-wrap">
                  {skill.tags.map(t => <Badge key={t} variant="secondary" className="text-[10px]">{t}</Badge>)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-sm text-gray-500 mb-2">历史版本</div>
              <div className="space-y-1">
                {skill.versions.map((v) => (
                  <div
                    key={v.version}
                    className={`flex items-center justify-between p-2 rounded text-sm cursor-pointer ${selectedVersion === v.version ? 'bg-blue-50' : 'hover:bg-gray-50'}`}
                    onClick={() => handleVersionClick(v.version)}
                  >
                    <div>
                      <span className={selectedVersion === v.version ? 'font-medium text-blue-600' : ''}>{v.version}</span>
                      {skill.versions[0]?.version === v.version && <Badge variant="outline" className="ml-1 text-[10px]">最新</Badge>}
                      <div className="text-xs text-gray-400">{formatSize(v.file_size)}</div>
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