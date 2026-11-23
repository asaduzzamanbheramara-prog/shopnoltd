import React, { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

const API = (import.meta.env.VITE_API_BASE || import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'https://api.shopnoltd.dpdns.org').replace(/\/+$/, '')
const MAX_BYTES = 25 * 1024 * 1024

async function storage(path, options = {}) {
  const token = localStorage.getItem('shopno_token')
  if (!token) throw new Error('Please sign in to access your private files.')
  const headers = { ...(options.headers || {}), Authorization: `Bearer ${token}` }
  const response = await fetch(`${API}/api/v1/storage/drive${path}`, { ...options, headers })
  if (!response.ok) {
    let message = `Storage request failed (${response.status})`
    try { const body = await response.json(); message = body.detail || message } catch {}
    throw new Error(message)
  }
  return response
}

function formatSize(bytes = 0) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function CloudStorage() {
  const [files, setFiles] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const refresh = useCallback(async () => {
    setError('')
    try {
      const response = await storage('')
      setFiles(await response.json())
    } catch (err) { setError(err.message) }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  async function upload(event) {
    const selected = Array.from(event.target.files || [])
    event.target.value = ''
    if (!selected.length) return
    const tooLarge = selected.find(file => file.size > MAX_BYTES)
    if (tooLarge) { setError(`${tooLarge.name} exceeds the 25 MB per-file limit.`); return }
    setBusy(true); setError(''); setNotice('')
    try {
      for (const file of selected) {
        const form = new FormData()
        form.append('file', file)
        await storage(`/${encodeURIComponent(file.name)}`, { method: 'POST', body: form })
      }
      setNotice(`${selected.length} file(s) uploaded successfully.`)
      await refresh()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function download(file) {
    setBusy(true); setError('')
    try {
      const response = await storage(`/${file.name.split('/').map(encodeURIComponent).join('/')}`)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = file.name.split('/').pop(); anchor.click()
      URL.revokeObjectURL(url)
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function remove(file) {
    if (!window.confirm(`Delete "${file.name}" permanently?`)) return
    setBusy(true); setError(''); setNotice('')
    try {
      await storage(`/${file.name.split('/').map(encodeURIComponent).join('/')}`, { method: 'DELETE' })
      setNotice(`${file.name} deleted.`)
      await refresh()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return <main style={{ minHeight: '100vh', background: '#f1f5f9', color: '#0f172a', fontFamily: 'Inter,system-ui,sans-serif', padding: '28px clamp(16px,4vw,48px)' }}>
    <div style={{ maxWidth: 1120, margin: '0 auto' }}>
      <header style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 30 }}>
        <Link to="/" style={{ color: '#0369a1', fontWeight: 800, textDecoration: 'none' }}>← Shopnoltd</Link>
        <span style={{ color: '#64748b', fontSize: 13 }}>PRIVATE · ACCOUNT-ISOLATED STORAGE</span>
      </header>
      <section style={{ background: 'linear-gradient(130deg,#075985,#0ea5e9)', color: 'white', borderRadius: 22, padding: 'clamp(24px,5vw,44px)', boxShadow: '0 14px 35px rgba(2,132,199,.18)' }}>
        <div style={{ fontSize: 38 }}>☁️</div>
        <h1 style={{ fontSize: 'clamp(30px,5vw,44px)', margin: '8px 0' }}>Shopnoltd Cloud Storage</h1>
        <p style={{ maxWidth: 650, lineHeight: 1.65, margin: 0, color: '#e0f2fe' }}>Your private files, accessible from your Shopnoltd account. Upload, download and manage files securely.</p>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 24 }}>
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, background: 'white', color: '#075985', borderRadius: 10, padding: '12px 18px', fontWeight: 800, cursor: busy ? 'wait' : 'pointer', opacity: busy ? .6 : 1 }}>
            {busy ? 'Working…' : '＋ Upload files'}
            <input type="file" multiple disabled={busy} onChange={upload} style={{ display: 'none' }} />
          </label>
          <button onClick={refresh} disabled={busy} style={{ border: '1px solid #bae6fd', color: 'white', background: 'rgba(255,255,255,.12)', borderRadius: 10, padding: '12px 18px', fontWeight: 700, cursor: 'pointer' }}>↻ Refresh</button>
        </div>
      </section>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, margin: '28px 0 14px', flexWrap: 'wrap' }}>
        <div><h2 style={{ margin: 0, fontSize: 22 }}>My files</h2><p style={{ margin: '5px 0 0', color: '#64748b', fontSize: 14 }}>{files.length} file(s) · Up to 25 MB per file</p></div>
        <span style={{ color: '#64748b', fontSize: 13 }}>Files are private to your signed-in account</span>
      </div>
      {error && <div role="alert" style={{ background: '#fef2f2', color: '#991b1b', padding: 14, borderRadius: 10, marginBottom: 14 }}>{error}</div>}
      {notice && <div role="status" style={{ background: '#ecfdf5', color: '#065f46', padding: 14, borderRadius: 10, marginBottom: 14 }}>{notice}</div>}
      <section style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden' }}>
        {files.length === 0 ? <div style={{ textAlign: 'center', padding: '54px 20px' }}><div style={{ fontSize: 42 }}>📂</div><h3 style={{ marginBottom: 6 }}>No files yet</h3><p style={{ color: '#64748b', margin: 0 }}>Choose Upload files to add your first document or image.</p></div> :
          <div>{files.map(file => <article key={file.name} style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '16px 20px', borderBottom: '1px solid #f1f5f9', flexWrap: 'wrap' }}>
            <span style={{ fontSize: 26 }}>📄</span><div style={{ flex: 1, minWidth: 160 }}><strong style={{ overflowWrap: 'anywhere' }}>{file.name}</strong><div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{formatSize(file.size)}{file.last_modified ? ` · ${new Date(file.last_modified).toLocaleString()}` : ''}</div></div>
            <button disabled={busy} onClick={() => download(file)} style={{ border: '1px solid #bae6fd', color: '#0369a1', background: 'white', borderRadius: 8, padding: '8px 12px', cursor: 'pointer' }}>Download</button>
            <button disabled={busy} onClick={() => remove(file)} style={{ border: '1px solid #fecaca', color: '#b91c1c', background: 'white', borderRadius: 8, padding: '8px 12px', cursor: 'pointer' }}>Delete</button>
          </article>)}</div>}
      </section>
      <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.6, marginTop: 18 }}>Security: storage requests require your Shopnoltd sign-in token and each account is restricted to its own object prefix. Maximum upload size: 25 MB per file.</p>
    </div>
  </main>
}
