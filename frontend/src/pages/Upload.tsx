import { useState, useRef } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { apiFetch } from '../api/client'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Badge } from '../components/ui/badge'
import { Card, CardContent } from '../components/ui/card'
import { ArrowLeft, FolderOpen, X } from 'lucide-react'

function parseFrontmatterField(mdContent: string, field: string): string {
  const trimmed = mdContent.trimStart()
  if (!trimmed.startsWith('---')) return ''
  const end = trimmed.indexOf('\n---', 3)
  if (end === -1) return ''
  const fm = trimmed.slice(3, end)
  const regex = new RegExp(`^${field}\\s*:\\s*(.+)$`, 'im')
  const match = fm.match(regex)
  return match ? match[1].trim().replace(/^["']|["']$/g, '') : ''
}

function extractDescFromFiles(files: { name: string; data: Uint8Array }[]): string {
  for (const f of files) {
    if (f.name.endsWith('SKILL.md') || f.name.endsWith('skill.md')) {
      const content = new TextDecoder().decode(f.data)
      return parseFrontmatterField(content, 'description')
    }
  }
  return ''
}

function crc32(data: Uint8Array): number {
  let crc = 0xFFFFFFFF
  for (let i = 0; i < data.length; i++) {
    crc ^= data[i]
    for (let j = 0; j < 8; j++) {
      crc = (crc >>> 1) ^ (crc & 1 ? 0xEDB88320 : 0)
    }
  }
  return (crc ^ 0xFFFFFFFF) >>> 0
}

function createZip(files: { name: string; data: Uint8Array }[]): Blob {
  const encoder = new TextEncoder()
  const fileChunks: Uint8Array[] = []
  const centralEntries: { header: Uint8Array; offset: number }[] = []
  let offset = 0

  for (const f of files) {
    const nameBytes = encoder.encode(f.name)
    const crc = crc32(f.data)

    const localHeader = new Uint8Array(30 + nameBytes.length)
    const lh = new DataView(localHeader.buffer)
    lh.setUint32(0, 0x04034b50, true)
    lh.setUint16(8, 0, true)
    lh.setUint32(14, crc, true)
    lh.setUint32(18, f.data.length, true)
    lh.setUint32(22, f.data.length, true)
    lh.setUint16(26, nameBytes.length, true)
    localHeader.set(nameBytes, 30)

    const centHeader = new Uint8Array(46 + nameBytes.length)
    const ch = new DataView(centHeader.buffer)
    ch.setUint32(0, 0x02014b50, true)
    ch.setUint32(16, crc, true)
    ch.setUint32(20, f.data.length, true)
    ch.setUint32(24, f.data.length, true)
    ch.setUint16(28, nameBytes.length, true)
    ch.setUint32(42, offset, true)
    centHeader.set(nameBytes, 46)

    fileChunks.push(localHeader, f.data)
    centralEntries.push({ header: centHeader, offset })
    offset += localHeader.length + f.data.length
  }

  const centBufs = centralEntries.map(c => c.header)
  const centStart = offset
  const centSize = centBufs.reduce((s, c) => s + c.length, 0)

  const eocd = new Uint8Array(22)
  const ev = new DataView(eocd.buffer)
  ev.setUint32(0, 0x06054b50, true)
  ev.setUint16(8, files.length, true)
  ev.setUint16(10, files.length, true)
  ev.setUint32(12, centSize, true)
  ev.setUint32(16, centStart, true)

  const all: BlobPart[] = [...fileChunks, ...centBufs, eocd] as any
  return new Blob(all, { type: 'application/zip' })
}

async function readFilesFromEntry(entry: FileSystemDirectoryEntry, root: boolean = true): Promise<{ name: string; data: Uint8Array }[]> {
  const results: { name: string; data: Uint8Array }[] = []

  async function walk(dir: FileSystemDirectoryEntry, prefix: string) {
    const entries = await new Promise<FileSystemEntry[]>((resolve, reject) => {
      const reader = dir.createReader()
      const readAll: FileSystemEntry[] = []
      function next() {
        reader.readEntries((batch) => {
          if (batch.length === 0) { resolve(readAll); return }
          readAll.push(...batch)
          next()
        }, reject)
      }
      next()
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

  await walk(entry, root ? '' : entry.name)
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

async function listFilesFromEntry(entry: FileSystemDirectoryEntry): Promise<number> {
  let count = 0
  async function countFiles(dir: FileSystemDirectoryEntry) {
    const entries = await new Promise<FileSystemEntry[]>((resolve, reject) => {
      const reader = dir.createReader()
      const all: FileSystemEntry[] = []
      function next() {
        reader.readEntries((batch) => {
          if (batch.length === 0) { resolve(all); return }
          all.push(...batch)
          next()
        }, reject)
      }
      next()
    })
    for (const e of entries) {
      if (e.isDirectory) {
        await countFiles(e as FileSystemDirectoryEntry)
      } else {
        count++
      }
    }
  }
  await countFiles(entry)
  return count
}

export default function Upload() {
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

  async function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const items = e.dataTransfer.items
    if (items.length === 0) return
    const all: { name: string; data: Uint8Array }[] = []
    let name = ''
    for (const item of Array.from(items)) {
      const entry = (item as any).webkitGetAsEntry?.()
      if (!entry || !entry.isDirectory) continue
      name = entry.name
      const tree = await readFilesFromEntry(entry, false)
      for (const f of tree) all.push(f)
      break
    }
    if (all.length > 0) {
      setRawFiles(all)
      setFolderName(name)
      setFileCount(all.length)
      setDisplayName(name)
      setDescription(extractDescFromFiles(all))
    }
  }

  async function handleSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files
    if (!files || files.length === 0) return
    const name = files[0].webkitRelativePath?.split('/')[0] || 'skill'
    const all = await readFilesFromFileList(files)
    setRawFiles(all)
    setFolderName(name)
    setFileCount(all.length)
    setDisplayName(name)
    setDescription(extractDescFromFiles(all))
  }

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault()
    if (rawFiles.length === 0) { toast.error('请选择文件夹'); return }
    setUploading(true)
    try {
      const zipBlob = createZip(rawFiles)
      const formData = new FormData()
      formData.append('file', zipBlob, `${folderName}.zip`)
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
    if (t && !tags.includes(t)) { setTags([...tags, t]); setTagInput('') }
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
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <input
                ref={inputRef}
                type="file"
                {...({ webkitdirectory: '', directory: '' } as any)}
                className="hidden"
                onChange={handleSelect}
              />
              <FolderOpen className="h-8 w-8 mx-auto text-gray-400 mb-2" />
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