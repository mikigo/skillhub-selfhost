import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, Upload as UploadIcon, X } from 'lucide-react'

export default function Upload() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [skillName, setSkillName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [version, setVersion] = useState('')
  const [releaseNotes, setReleaseNotes] = useState('')
  const [uploading, setUploading] = useState(false)

  if (!user) { navigate('/login'); return null }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (!file) { toast.error('请选择文件'); return }
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('display_name', displayName)
    formData.append('description', description)
    formData.append('tags', JSON.stringify(tags))
    if (version) formData.append('version', version)
    if (releaseNotes) formData.append('release_notes', releaseNotes)

    try {
      const resp = await apiFetch('/api/skills/', { method: 'POST', body: formData })
      if (!resp.ok) {
        const data = await resp.json()
        throw new Error(data.detail)
      }
      toast.success('上传成功')
      navigate('/my')
    } catch (err: any) {
      toast.error(err.message)
    } finally {
      setUploading(false)
    }
  }

  function addTag() {
    const t = tagInput.trim()
    if (t && !tags.includes(t)) {
      setTags([...tags, t])
      setTagInput('')
    }
  }

  return (
    <div>
      <Link to="/my" className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4">
        <ArrowLeft className="h-4 w-4 mr-1" />返回我的技能
      </Link>
      <Card>
        <CardContent className="p-6">
          <h2 className="text-lg font-bold mb-4">上传新 Skill</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-gray-50"
              onDragOver={e => e.preventDefault()}
              onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files[0]; if (f) { setFile(f); setSkillName(f.name.replace('.tar.gz', '').replace('.tgz', '')) } }}
              onClick={() => document.getElementById('file-upload')?.click()}
            >
              <input id="file-upload" type="file" accept=".tar.gz,.tgz" className="hidden"
                onChange={e => {
                  const f = e.target.files?.[0]
                  if (f) { setFile(f); setSkillName(f.name.replace('.tar.gz', '').replace('.tgz', '')) }
                }}
              />
              <UploadIcon className="h-8 w-8 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">{file ? file.name : '拖拽 tar.gz 到此处或点击选择文件'}</p>
            </div>

            <div><Label>skill 名称</Label><Input value={skillName} readOnly className="bg-gray-50" /><p className="text-xs text-gray-400">从目录名自动提取</p></div>
            <div><Label>展示名称</Label><Input value={displayName} onChange={e => setDisplayName(e.target.value)} required /></div>
            <div><Label>描述</Label><Input value={description} onChange={e => setDescription(e.target.value)} required /></div>
            <div>
              <Label>标签</Label>
              <div className="flex gap-1 flex-wrap mb-1">
                {tags.map(t => <Badge key={t} variant="secondary" className="cursor-pointer" onClick={() => setTags(tags.filter(x => x !== t))}>{t} <X className="h-3 w-3 ml-1" /></Badge>)}
              </div>
              <div className="flex gap-1">
                <Input value={tagInput} onChange={e => setTagInput(e.target.value)} placeholder="添加标签" onKeyDown={e => { if (e.key === 'Enter') { e.preventDefault(); addTag() } }} />
                <Button type="button" variant="outline" size="sm" onClick={addTag}>添加</Button>
              </div>
            </div>
            <div><Label>版本（留空自动追加小版本）</Label><Input value={version} onChange={e => setVersion(e.target.value)} placeholder="如 1.0.0" /></div>
            <div><Label>更新说明（可选）</Label><Input value={releaseNotes} onChange={e => setReleaseNotes(e.target.value)} /></div>

            <Button type="submit" disabled={uploading} className="w-full">
              {uploading ? '上传中...' : '上传'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}