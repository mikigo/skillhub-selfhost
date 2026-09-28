import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useAuth } from '../contexts/AuthContext'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, Upload as UploadIcon, FolderOpen, X, Loader2 } from 'lucide-react'

function pad512(n: number): number {
  return Math.ceil(n / 512) * 512
}

function octal(n: number, digits: number): string {
  return n.toString(8).padStart(digits, '0')
}

function tarHeader(name: string, size: number): Uint8Array {
  const header = new Uint8Array(512)
  const encoder = new TextEncoder()
  const set = (offset: number, value: string) => {
    header.set(encoder.encode(value).slice(0, value.length), offset)
  }
  set(0, name.slice(0, 100))
  set(100, octal(0o644, 7) + '\0')
  set(108, octal(0, 7) + '\0')
  set(116, octal(0, 7) + '\0')
  set(124, octal(size, 11) + ' ')
  set(136, octal(Math.floor(Date.now() / 1000), 11) + ' ')
  set(148, '        ')
  set(156, '0')
  set(257, 'ustar\0')
  set(263, '00')

  let sum = 0
  for (let i = 0; i < 512; i++) {
    sum += i >= 148 && i < 156 ? 32 : header[i]
  }
  set(148, octal(sum, 6) + '\0 ')
  return header
}

async function createTarGz(files: { name: string; data: Uint8Array }[]): Promise<Blob> {
  const chunks: Uint8Array[] = []

  for (const f of files) {
    chunks.push(tarHeader(f.name, f.data.length))
    const padded = new Uint8Array(pad512(f.data.length))
    padded.set(f.data)
    chunks.push(padded)
  }

  chunks.push(new Uint8Array(1024))

  const totalLen = chunks.reduce((s, c) => s + c.length, 0)
  const tar = new Uint8Array(totalLen)
  let offset = 0
  for (const c of chunks) {
    tar.set(c, offset)
    offset += c.length
  }

  const stream = new Blob([tar]).stream()
  const compressed = stream.pipeThrough(new CompressionStream('gzip'))
  return new Response(compressed).blob()
}

async function readFilesFromEntry(entry: FileSystemDirectoryEntry): Promise<{ name: string; data: Uint8Array }[]> {
  const results: { name: string; data: Uint8Array }[] = []

  async function walk(dir: FileSystemDirectoryEntry, prefix: string) {
    const entries = await new Promise<FileSystemEntry[]>((resolve, reject) => {
      const reader = dir.createReader()
      reader.readEntries(resolve, reject)
    })

    for (const e of entries) {
      const fullPath = prefix ? `${prefix}/${e.name}` : e.name
      if (e.isDirectory) {
        await walk(e as FileSystemDirectoryEntry, fullPath)
      } else {
        const file = await new Promise<File>((resolve, reject) => {
          (e as FileSystemFileEntry).file(resolve, reject)
        })
        const buf = await file.arrayBuffer()
        results.push({ name: fullPath, data: new Uint8Array(buf) })
      }
    }
  }

  await walk(entry, '')
  return results
}

async function readFilesFromFileList(files: FileList): Promise<{ name: string; data: Uint8Array }[]> {
  const results: { name: string; data: Uint8Array }[] = []
  for (const file of Array.from(files)) {
    const buf = await file.arrayBuffer()
    const relPath = (file as any).webkitRelativePath || file.name
    results.push({ name: relPath, data: new Uint8Array(buf) })
  }
  return results
}

async function handleDropFolder(
  e: React.DragEvent,
  onDone: (files: { name: string; data: Uint8Array }[], folderName: string) => void,
) {
  e.preventDefault()
  const items = e.dataTransfer.items
  if (items.length === 0) return

  const all: { name: string; data: Uint8Array }[] = []

  for (const item of Array.from(items)) {
    const entry = (item as any).webkitGetAsEntry?.()
    if (!entry) continue

    const tree = await readFilesFromEntry(entry)
    const folder = entry.name
    for (const f of tree) {
      all.push({ name: `${folder}/${f.name}`, data: f.data })
    }
  }

  if (all.length > 0) {
    const firstEntry = (items[0] as any).webkitGetAsEntry?.()
    onDone(all, firstEntry?.name || 'skill')
  }
}

export default function Upload() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [folderName, setFolderName] = useState('')
  const [fileCount, setFileCount] = useState(0)
  const [rawFiles, setRawFiles] = useState<{ name: string; data: Uint8Array }[]>([])
  const [displayName, setDisplayName] = useState('')
  const [description, setDescription] = useState('')
  const [tags, setTags] = useState<string[]>([])
  const [tagInput, setTagInput] = useState('')
  const [version, setVersion] = useState('')
  const [releaseNotes, setReleaseNotes] = useState('')
  const [uploading, setUploading] = useState(false)
  const [compressing, setCompressing] = useState(false)

  if (!user) { navigate('/login'); return null }

  async function handleFiles(files: { name: string; data: Uint8Array }[], name: string) {
    setCompressing(true)
    setRawFiles(files)
    setFolderName(name)
    setFileCount(files.length)
    setDisplayName(name)
    try {
      await createTarGz(files)
    } finally {
      setCompressing(false)
    }
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (rawFiles.length === 0) { toast.error('请选择文件夹'); return }
    setUploading(true)
    try {
      const tarBlob = await createTarGz(rawFiles)
      const formData = new FormData()
      formData.append('file', tarBlob, `${folderName}.tar.gz`)
      formData.append('display_name', displayName)
      formData.append('description', description)
      formData.append('tags', JSON.stringify(tags))
      if (version) formData.append('version', version)
      if (releaseNotes) formData.append('release_notes', releaseNotes)

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
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:bg-gray-50"
              onDragOver={e => e.preventDefault()}
              onDrop={e => handleDropFolder(e, handleFiles)}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                {...({ webkitdirectory: '', directory: '' } as any)}
                className="hidden"
                onChange={async e => {
                  const files = e.target.files
                  if (!files || files.length === 0) return
                  const name = files[0].webkitRelativePath?.split('/')[0] || 'skill'
                  const all = await readFilesFromFileList(files)
                  handleFiles(all, name)
                }}
              />
              {compressing ? (
                <Loader2 className="h-8 w-8 mx-auto text-gray-400 mb-2 animate-spin" />
              ) : (
                <FolderOpen className="h-8 w-8 mx-auto text-gray-400 mb-2" />
              )}
              <p className="text-sm text-gray-500">
                {folderName
                  ? `${folderName} (${fileCount} 个文件)`
                  : '拖拽文件夹到此处或点击选择文件夹'}
              </p>
            </div>

            <div><Label>skill 名称</Label><Input value={folderName} readOnly className="bg-gray-50" /><p className="text-xs text-gray-400">从文件夹名自动提取</p></div>
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

            <Button type="submit" disabled={uploading || rawFiles.length === 0} className="w-full">
              {uploading ? '上传中...' : '上传'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}