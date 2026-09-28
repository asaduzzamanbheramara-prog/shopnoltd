import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, ChevronDown, ChevronUp, Film, Loader2, Plus, Trash2, Upload, XCircle } from 'lucide-react'

const API_BASE = import.meta.env.VITE_STORAGE_API_URL || 'https://storage-service.shopnoltd.dpdns.org'
const PROFILES = [
  { slug: 'data-management', label: 'Data Management & Research' },
  { slug: 'interior-business', label: 'Business & Interior Design' },
]

function headers(json = false) {
  const token = localStorage.getItem('shopno_token')
  const h = {}
  if (token) h.Authorization = `Bearer ${token}`
  if (json) h['Content-Type'] = 'application/json'
  return h
}

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}/api/v1/profile-videos${path}`, { ...options, headers: { ...headers(!!options.body), ...(options.headers || {}) } })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || text || `HTTP ${response.status}`)
  return data
}

function Button({ children, ...props }) {
  return <button {...props} style={{ border: '1px solid #cbd5e1', borderRadius: 8, padding: '8px 12px', background: 'white', cursor: props.disabled ? 'not-allowed' : 'pointer', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 6 }}>{children}</button>
}

export default function AdminProfileVideos() {
  const [profile, setProfile] = useState(PROFILES[0].slug)
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [file, setFile] = useState(null)
  const [form, setForm] = useState({ title: '', description: '' })
  const [embed, setEmbed] = useState({ title: '', description: '', url: '' })
  const [progress, setProgress] = useState(0)

  async function load() {
    setLoading(true); setError(''); setMessage('')
    try { setItems(await api(`/admin/${profile}`) || []) } catch (e) { setError(`Could not load videos: ${e.message}`) }
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [profile])

  async function upload() {
    if (!file || !form.title.trim()) return setError('Choose a video and enter a title.')
    setBusy(true); setProgress(0); setError(''); setMessage('')
    let uploadId = null
    try {
      const start = await api('/uploads', { method: 'POST', body: JSON.stringify({ profile_slug: profile, title: form.title.trim(), description: form.description.trim() || null, filename: file.name, content_type: file.type, size: file.size }) })
      uploadId = start.id || start.upload_id
      const totalParts = Number(start.total_parts || Math.ceil(file.size / (8 * 1024 * 1024)))
      const chunkSize = Number(start.chunk_size || 8 * 1024 * 1024)
      for (let part = 1; part <= totalParts; part++) {
        const chunk = file.slice((part - 1) * chunkSize, Math.min(part * chunkSize, file.size))
        const response = await fetch(`${API_BASE}/api/v1/profile-videos/uploads/${encodeURIComponent(uploadId)}/parts/${part}`, { method: 'PUT', headers: { ...headers(), 'Content-Type': file.type || 'application/octet-stream' }, body: chunk })
        if (!response.ok) { const t = await response.text(); throw new Error(t || `Part ${part} failed (HTTP ${response.status})`) }
        setProgress(Math.round(part / totalParts * 100))
      }
      await api(`/uploads/${encodeURIComponent(uploadId)}/complete`, { method: 'POST' })
      setFile(null); setForm({ title: '', description: '' }); setProgress(100); setMessage('Video uploaded successfully. It is published according to the storage-service default; verify the Published status below.'); await load()
    } catch (e) {
      setError(`Upload failed: ${e.message}`)
      if (uploadId) {
        try {
          await api(`/uploads/${encodeURIComponent(uploadId)}`, { method: 'DELETE' })
        } catch (_) {}
      }
    } finally {
      setBusy(false)
    }
  }

  async function addEmbed() {
    if (!embed.title.trim() || !embed.url.trim()) return setError('Enter an external video title and HTTPS YouTube, Vimeo, or direct MP4/WebM URL.')
    setBusy(true); setError(''); setMessage('')
    try {
      await api('/embeds', { method: 'POST', body: JSON.stringify({ profile_slug: profile, title: embed.title.trim(), description: embed.description.trim() || null, url: embed.url.trim() }) })
      setEmbed({ title: '', description: '', url: '' }); setMessage('External video added.'); await load()
    } catch (e) { setError(`External video failed: ${e.message}`) }
    finally { setBusy(false) }
  }

  async function patch(id, body) { setBusy(true); setError(''); try { await api(`/items/${encodeURIComponent(id)}`, { method: 'PATCH', body: JSON.stringify(body) }); await load() } catch (e) { setError(e.message) } finally { setBusy(false) } }
  async function remove(id) { if (!window.confirm('Delete this profile video permanently?')) return; setBusy(true); setError(''); try { await api(`/items/${encodeURIComponent(id)}`, { method: 'DELETE' }); setMessage('Video deleted.'); await load() } catch (e) { setError(`Delete failed: ${e.message}`) } finally { setBusy(false) } }
  async function move(index, direction) {
    const next = [...items]; const target = index + direction
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    setBusy(true); setError('')
    try { await api('/reorder', { method: 'POST', body: JSON.stringify({ profile_slug: profile, ids: next.map(x => x.id) }) }); setItems(next) }
    catch (e) { setError(`Reorder failed: ${e.message}`) } finally { setBusy(false) }
  }

  return <div style={{ maxWidth: 1100, margin: '0 auto', padding: '30px 18px 60px' }}>
    <div style={{ marginBottom: 22 }}><Link to="/admin" style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: '#0369a1', fontWeight: 700, textDecoration: 'none', marginBottom: 12 }}><ArrowLeft size={16} /> Admin dashboard</Link><h1 style={{ margin: 0 }}>Profile Video Management</h1><p style={{ color: '#64748b', lineHeight: 1.6 }}>Upload and publish profile videos through the protected storage service. Videos are stored in MinIO and indexed in PostgreSQL.</p></div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18 }}>
      <section style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 18 }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Profile</h2><select value={profile} onChange={e => setProfile(e.target.value)} style={{ width: '100%', padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }}>{PROFILES.map(p => <option key={p.slug} value={p.slug}>{p.label}</option>)}</select>
        <h2 style={{ fontSize: 18, marginTop: 24 }}>Upload video</h2>
        <input type="file" accept="video/mp4,video/webm,.mp4,.webm" onChange={e => setFile(e.target.files?.[0] || null)} disabled={busy} />
        <input placeholder="Title" value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} style={{ width: '100%', boxSizing: 'border-box', marginTop: 10, padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }} />
        <textarea placeholder="Description (optional)" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} rows={3} style={{ width: '100%', boxSizing: 'border-box', marginTop: 10, padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }} />
        <Button onClick={upload} disabled={busy || !file}>{busy ? <Loader2 size={15} /> : <Upload size={15} />} {busy ? `Uploading ${progress}%` : 'Upload & publish'}</Button>
        {busy && progress > 0 && <progress value={progress} max="100" style={{ width: '100%', marginTop: 10 }} />}
      </section>
      <section style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 18 }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>Add YouTube / Vimeo</h2>
        <input placeholder="Title" value={embed.title} onChange={e => setEmbed({ ...embed, title: e.target.value })} style={{ width: '100%', boxSizing: 'border-box', padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }} />
        <input placeholder="HTTPS video URL" value={embed.url} onChange={e => setEmbed({ ...embed, url: e.target.value })} style={{ width: '100%', boxSizing: 'border-box', marginTop: 10, padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }} />
        <textarea placeholder="Description (optional)" value={embed.description} onChange={e => setEmbed({ ...embed, description: e.target.value })} rows={3} style={{ width: '100%', boxSizing: 'border-box', marginTop: 10, padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }} />
        <Button onClick={addEmbed} disabled={busy}><Plus size={15} /> Add external video</Button>
      </section>
    </div>
    {(message || error) && <div style={{ marginTop: 18, padding: 12, borderRadius: 8, background: error ? '#fef2f2' : '#f0fdf4', color: error ? '#991b1b' : '#166534', display: 'flex', gap: 8, alignItems: 'center' }}>{error ? <XCircle size={16} /> : <CheckCircle2 size={16} />}{error || message}</div>}
    <section style={{ marginTop: 24 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}><h2 style={{ fontSize: 20 }}>Managed videos {loading ? '…' : `(${items.length})`}</h2><Button onClick={load} disabled={loading}>Refresh</Button></div>
      {items.length === 0 && !loading && <div style={{ padding: 24, border: '1px dashed #cbd5e1', borderRadius: 10, color: '#64748b' }}><Film size={18} style={{ verticalAlign: 'middle', marginRight: 6 }} />No videos for this profile yet.</div>}
      <div style={{ display: 'grid', gap: 14 }}>{items.map((item, index) => <article key={item.id} style={{ border: '1px solid #e2e8f0', borderRadius: 12, padding: 14, display: 'grid', gridTemplateColumns: 'minmax(240px, 360px) 1fr', gap: 16 }}>
        <div>{item.source_type === 'upload' ? <video controls preload="metadata" playsInline src={`${API_BASE}/api/v1/profile-videos/stream/${encodeURIComponent(item.id)}`} style={{ width: '100%', maxHeight: 210, borderRadius: 8, background: '#0f172a' }} /> : item.embed_provider === 'youtube' ? <iframe title={item.title} src={`https://www.youtube.com/embed/${item.embed_ref}`} style={{ width: '100%', aspectRatio: '16/9', border: 0, borderRadius: 8 }} allowFullScreen /> : item.embed_provider === 'vimeo' ? <iframe title={item.title} src={`https://player.vimeo.com/video/${item.embed_ref}`} style={{ width: '100%', aspectRatio: '16/9', border: 0, borderRadius: 8 }} allowFullScreen /> : <video controls src={item.embed_ref} style={{ width: '100%', maxHeight: 210, borderRadius: 8 }} />}</div>
        <div><input value={item.title || ''} onChange={e => setItems(items.map(x => x.id === item.id ? { ...x, title: e.target.value } : x))} style={{ width: '100%', boxSizing: 'border-box', padding: 9, borderRadius: 7, border: '1px solid #cbd5e1', fontWeight: 700 }} /><textarea value={item.description || ''} onChange={e => setItems(items.map(x => x.id === item.id ? { ...x, description: e.target.value } : x))} rows={3} style={{ width: '100%', boxSizing: 'border-box', marginTop: 8, padding: 9, borderRadius: 7, border: '1px solid #cbd5e1' }} /><div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}><Button onClick={() => patch(item.id, { title: item.title, description: item.description })} disabled={busy}>Save</Button><Button onClick={() => patch(item.id, { published: !item.published })} disabled={busy}>{item.published ? 'Unpublish' : 'Publish'}</Button><Button onClick={() => move(index, -1)} disabled={busy || index === 0}><ChevronUp size={15} />Up</Button><Button onClick={() => move(index, 1)} disabled={busy || index === items.length - 1}><ChevronDown size={15} />Down</Button><Button onClick={() => remove(item.id)} disabled={busy}><Trash2 size={15} />Delete</Button></div><small style={{ display: 'block', marginTop: 9, color: '#64748b' }}>{item.source_type} · {item.published ? 'Published' : 'Draft'} · {item.content_type || item.embed_provider || ''}</small></div>
      </article>)}</div>
    </section>
  </div>
}
