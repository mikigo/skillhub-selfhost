import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { skillPath } from '@/lib/skillPath'
import { useT } from '../contexts/I18nContext'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Info } from 'lucide-react'

export default function GitlabUploadForm() {
  const { t } = useT()
  const navigate = useNavigate()
  const [gitlabUrl, setGitlabUrl] = useState('')
  const [branch, setBranch] = useState('main')
  const [repoPath, setRepoPath] = useState('')
  const [uploading, setUploading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setUploading(true)
    try {
      const resp = await apiFetch('/api/skills/remote', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gitlab_url: gitlabUrl, branch, skill_path: repoPath }),
      })
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({} as any))
        // FastAPI 的 422 校验错误里 detail 是数组，不能直接当字符串用
        throw new Error(typeof data.detail === 'string' ? data.detail : t('upload.gitlabFailed'))
      }
      const data = await resp.json()
      toast.success(t('upload.gitlabSuccess'))
      // 同名 skill 可能有好几个，必须用响应里的作者一起拼地址
      navigate(skillPath(data.author.username, data.name))
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex gap-2 rounded-md border bg-muted/50 p-3 text-xs text-muted-foreground">
        <Info className="h-4 w-4 shrink-0 mt-0.5" />
        <span>{t('upload.gitlabHint')}</span>
      </div>

      <div>
        <Label>{t('upload.gitlabUrl')}</Label>
        <Input
          value={gitlabUrl}
          onChange={e => setGitlabUrl(e.target.value)}
          placeholder={t('upload.gitlabUrlPlaceholder')}
          autoComplete="off"
          spellCheck={false}
          required
        />
      </div>
      <div>
        <Label>{t('upload.gitlabBranch')}</Label>
        <Input value={branch} onChange={e => setBranch(e.target.value)} placeholder="main" required />
      </div>
      <div>
        <Label>{t('upload.gitlabPath')}</Label>
        <Input
          value={repoPath}
          onChange={e => setRepoPath(e.target.value)}
          placeholder={t('upload.gitlabPathPlaceholder')}
          autoComplete="off"
          spellCheck={false}
        />
        <p className="text-xs text-muted-foreground mt-1">{t('upload.gitlabNameNote')}</p>
      </div>

      <Button type="submit" disabled={uploading || !gitlabUrl || !branch} className="w-full">
        {uploading ? t('upload.gitlabUploading') : t('upload.gitlabUploadBtn')}
      </Button>
    </form>
  )
}
