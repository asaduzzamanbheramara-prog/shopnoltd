import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { tryRefresh } from '../lib/tokenRefresh'

const API_BASE = import.meta.env.VITE_STORAGE_API_URL || 'https://storage-service.shopnoltd.dpdns.org'
const PROFILE_API = '/api/v1/profiles'
const VIDEO_API = '/api/v1/profile-videos'
const EMPTY = { display_name: '', headline: '', summary: '', location: '', website: '', skills: [], experience: [], education: [], portfolio: [], visibility: 'private' }

function tokenHeaders(json = false, tokenOverride = null) {
  const token = tokenOverride || localStorage.getItem('shopno_token')
  return { ...(token ? { Authorization: 'Bearer ' + token } : {}), ...(json ? { 'Content-Type': 'application/json' } : {}) }
}

async function request(path, options = {}, base = API_BASE) {
  const send = token => fetch(base + path, { ...options, headers: { ...tokenHeaders(options.json, token), ...(options.headers || {}) } })
  let response = await send(localStorage.getItem('shopno_token'))
  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) response = await send(refreshed)
  }
  const body = await response.text()
  let data = null
  try { data = body ? JSON.parse(body) : null } catch { data = body }
  if (!response.ok) throw new Error(data?.detail || data?.message || body || 'Request failed (' + response.status + ')')
  return data
}

function listValue(value) { return Array.isArray(value) ? value.join('\n') : '' }

export default function MyProfessionalProfile() {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(EMPTY)
  const [videos, setVideos] = useState([])
  const [file, setFile] = useState(null)
  const [videoTitle, setVideoTitle] = useState('')
  const [videoDescription, setVideoDescription] = useState('')
  const [embed, setEmbed] = useState({ title: '', description: '', url: '' })
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function loadProfile() {
    const data = await request('/me')
    setProfile(data)
    setForm({ ...EMPTY, ...data, skills: listValue(data.skills), experience: listValue(data.experience), education: listValue(data.education), portfolio: listValue(data.portfolio) })
    return data
  }

  async function loadVideos(slug) {
    const data = await request(VIDEO_API + '/mine/' + encodeURIComponent(slug))
    setVideos(Array.isArray(data) ? data : [])
  }

  useEffect(() => {
    let active = true
    request('/me').then(async data => {
      if (!active) return
      setProfile(data)
      setForm({ ...EMPTY, ...data, skills: listValue(data.skills), experience: listValue(data.experience), education: listValue(data.education), portfolio: listValue(data.portfolio) })
      try { const items = await request(VIDEO_API + '/mine/' + encodeURIComponent(data.slug)); if (active) setVideos(Array.isArray(items) ? items : []) }
      catch (e) { if (active) setError('Profile loaded, but videos could not be loaded: ' + e.message) }
    }).catch(e => { if (active) setError(e.message) })
    return () => { active = false }
  }, [])

  function update(key, value) { setForm(current => ({ ...current, [key]: value })) }

  async function save(event) {
    event.preventDefault()
    setBusy(true); setError(''); setMessage('')
    try {
      const payload = { ...form }
      for (const key of ['skills', 'experience', 'education', 'portfolio']) payload[key] = String(form[key] || '').split('\n').map(x => x.trim()).filter(Boolean)
      const data = await request('/me', { method: 'PUT', body: JSON.stringify(payload), json: true })
      setProfile(data)
      setMessage('Professional profile saved.')
      await loadVideos(data.slug)
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  async function uploadVideo() {
    if (!profile || !file || !videoTitle.trim()) { setError('Choose a video and enter its title.'); return }
    if (!['video/mp4', 'video/webm'].includes(file.type) || file.size > 500 * 1024 * 1024) { setError('Use an MP4 or WebM video up to 500 MB.'); return }
    setBusy(true); setProgress(0); setError(''); setMessage('')
    let uploadId = null
    try {
      const start = await request(VIDEO_API + '/uploads', { method: 'POST', body: JSON.stringify({ profile_slug: profile.slug, title: videoTitle.trim(), description: videoDescription.trim() || null, filename: file.name, content_type: file.type, size: file.size }), json: true })
      uploadId = start.upload_id
      for (let part = 1; part <= start.total_parts; part++) {
        const chunk = file.slice((part - 1) * start.chunk_size, Math.min(part * start.chunk_size, file.size))
        await request(VIDEO_API + '/uploads/' + encodeURIComponent(uploadId) + '/parts/' + part, { method: 'PUT', body: chunk, headers: { 'Content-Type': file.type } })
        setProgress(Math.round(part / start.total_parts * 100))
      }
      await request(VIDEO_API + '/uploads/' + encodeURIComponent(uploadId) + '/complete', { method: 'POST' })
      setFile(null); setVideoTitle(''); setVideoDescription('')
      await loadVideos(profile.slug)
      setMessage('Video uploaded as a draft. Publish it below when it is ready for your profile visitors.')
    } catch (e) {
      setError('Video upload failed: ' + e.message)
      if (uploadId) { try { await request(VIDEO_API + '/uploads/' + encodeURIComponent(uploadId), { method: 'DELETE' }) } catch (_) {} }
    } finally { setBusy(false) }
  }

  async function addEmbed() {
    if (!profile || !embed.title.trim() || !embed.url.trim()) { setError('Enter the video title and an HTTPS video URL.'); return }
    setBusy(true); setError(''); setMessage('')
    try {
      await request(VIDEO_API + '/embeds', { method: 'POST', body: JSON.stringify({ profile_slug: profile.slug, ...embed }), json: true })
      setEmbed({ title: '', description: '', url: '' })
      await loadVideos(profile.slug)
      setMessage('Video embed added as a draft. Publish it when ready.')
    } catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  async function updateVideo(id, patch) {
    setBusy(true); setError(''); setMessage('')
    try { await request(VIDEO_API + '/items/' + encodeURIComponent(id), { method: 'PATCH', body: JSON.stringify(patch), json: true }); await loadVideos(profile.slug); setMessage('Video updated.') }
    catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  async function deleteVideo(id) {
    if (!window.confirm('Delete this video permanently?')) return
    setBusy(true); setError('')
    try { await request(VIDEO_API + '/items/' + encodeURIComponent(id), { method: 'DELETE' }); await loadVideos(profile.slug); setMessage('Video deleted.') }
    catch (e) { setError(e.message) }
    finally { setBusy(false) }
  }

  const shareUrl = profile ? window.location.origin + '/profile/' + profile.slug : ''
  const fields = [
    ['headline', 'Professional headline', 'e.g. Data Analyst · Research Specialist'],
    ['location', 'Professional location', 'City / country (optional)'],
    ['website', 'Website (HTTPS)', 'https://example.com'],
  ]

  return <main style={{ maxWidth: 1050, margin: '0 auto', padding: '30px 16px 80px', fontFamily: 'system-ui,sans-serif' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
      <div><p style={{ color: '#0284c7', fontWeight: 800, letterSpacing: '.08em' }}>MEMBER WORKSPACE</p><h1 style={{ margin: 0 }}>My professional profile</h1><p style={{ color: '#64748b' }}>Create your professional profile and manage your own videos.</p></div>
      <Link to="/account">Back to account</Link>
    </div>
    {error && <p role="alert" style={{ padding: 12, background: '#fef2f2', color: '#991b1b', borderRadius: 8 }}>{error}</p>}
    {message && <p role="status" style={{ padding: 12, background: '#f0fdf4', color: '#166534', borderRadius: 8 }}>{message}</p>}
    {!profile ? <p>Loading your profile…</p> : <>
      <section style={{ border: '1px solid #e2e8f0', borderRadius: 14, padding: 20, marginTop: 22 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}><div><b>Profile address</b><p style={{ margin: '6px 0', overflowWrap: 'anywhere' }}>{shareUrl}</p><small style={{ color: '#64748b' }}>Your profile is private until you change its visibility.</small></div><div style={{ display: 'flex', gap: 8, alignItems: 'center' }}><button type="button" onClick={() => navigator.clipboard?.writeText(shareUrl)} style={{ padding: '9px 12px' }}>Copy link</button><a href={shareUrl} target="_blank" rel="noreferrer">Preview</a></div></div>
      </section>
      <form onSubmit={save} style={{ border: '1px solid #e2e8f0', borderRadius: 14, padding: 20, marginTop: 18 }}>
        <h2>Professional details</h2>
        <label style={{ display: 'block', marginBottom: 12 }}>Display name<input required maxLength={160} value={form.display_name} onChange={e => update('display_name', e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5 }} /></label>
        {fields.map(([key, label, placeholder]) => <label key={key} style={{ display: 'block', marginBottom: 12 }}>{label}<input maxLength={key === 'headline' ? 240 : key === 'location' ? 160 : 512} placeholder={placeholder} value={form[key] || ''} onChange={e => update(key, e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5 }} /></label>)}
        <label style={{ display: 'block', marginBottom: 12 }}>Professional summary<textarea rows={5} maxLength={3000} value={form.summary || ''} onChange={e => update('summary', e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5 }} /></label>
        {['skills', 'experience', 'education', 'portfolio'].map(key => <label key={key} style={{ display: 'block', marginBottom: 12, textTransform: 'capitalize' }}>{key} (one entry per line)<textarea rows={3} value={form[key] || ''} onChange={e => update(key, e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5 }} /></label>)}
        <label style={{ display: 'block', marginBottom: 16 }}>Profile visibility<select value={form.visibility} onChange={e => update('visibility', e.target.value)} style={{ display: 'block', padding: 10, marginTop: 5 }}><option value="private">Private — only you can manage it</option><option value="unlisted">Unlisted — anyone with the link can view it</option><option value="public">Public — shareable and indexable</option></select></label>
        <button disabled={busy} type="submit" style={{ padding: '11px 18px', border: 0, borderRadius: 8, background: '#0369a1', color: 'white', fontWeight: 800 }}>{busy ? 'Saving…' : 'Save profile'}</button>
      </form>
      <section style={{ border: '1px solid #e2e8f0', borderRadius: 14, padding: 20, marginTop: 18 }}>
        <h2>My profile videos</h2><p style={{ color: '#64748b' }}>MP4/WebM uploads or HTTPS YouTube/Vimeo links. New videos remain drafts until you publish them.</p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 14 }}>
          <div><h3>Upload a video</h3><input type="file" accept="video/mp4,video/webm,.mp4,.webm" onChange={e => setFile(e.target.files?.[0] || null)} disabled={busy} /><input placeholder="Video title" value={videoTitle} onChange={e => setVideoTitle(e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 9, marginTop: 8 }} /><textarea placeholder="Description (optional)" rows={2} value={videoDescription} onChange={e => setVideoDescription(e.target.value)} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 9, marginTop: 8 }} /><button type="button" onClick={uploadVideo} disabled={busy || !file} style={{ marginTop: 8, padding: 10 }}>Upload video</button>{busy && progress > 0 && <progress value={progress} max="100" style={{ width: '100%' }} />}</div>
          <div><h3>Add YouTube / Vimeo</h3><input placeholder="Video title" value={embed.title} onChange={e => setEmbed({ ...embed, title: e.target.value })} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 9, marginBottom: 8 }} /><input placeholder="HTTPS video URL" value={embed.url} onChange={e => setEmbed({ ...embed, url: e.target.value })} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 9, marginBottom: 8 }} /><textarea placeholder="Description (optional)" rows={2} value={embed.description} onChange={e => setEmbed({ ...embed, description: e.target.value })} style={{ display: 'block', width: '100%', boxSizing: 'border-box', padding: 9 }} /><button type="button" onClick={addEmbed} disabled={busy} style={{ marginTop: 8, padding: 10 }}>Add video link</button></div>
        </div>
        <div style={{ marginTop: 20, display: 'grid', gap: 10 }}>{videos.map(video => <article key={video.id} style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 12, display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><div><b>{video.title}</b><p style={{ margin: '4px 0', color: '#64748b' }}>{video.description || 'No description'} · {video.source_type} · {video.published ? 'Published' : 'Draft'}</p></div><div style={{ display: 'flex', gap: 8, alignItems: 'center' }}><button type="button" disabled={busy} onClick={() => updateVideo(video.id, { published: !video.published })}>{video.published ? 'Unpublish' : 'Publish'}</button><button type="button" disabled={busy} onClick={() => deleteVideo(video.id)}>Delete</button></div></article>)}{videos.length === 0 && <p style={{ color: '#64748b' }}>No videos yet.</p>}</div>
      </section>
    </>}
  </main>
}
