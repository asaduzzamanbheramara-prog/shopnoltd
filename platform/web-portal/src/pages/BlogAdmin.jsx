import React, { useEffect, useState } from 'react'

const EMPTY = { id: null, title: '', slug: '', excerpt: '', content: '', cover_image: '', status: 'draft' }

function authHeaders() {
  const token = localStorage.getItem('shopno_token')
  return token ? { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } : { 'Content-Type': 'application/json' }
}

export default function BlogAdmin() {
  const [posts, setPosts] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    const r = await fetch('/api/v1/blog/admin', { headers: authHeaders() })
    if (!r.ok) throw new Error(`Unable to load blog admin (${r.status})`)
    setPosts(await r.json())
  }

  useEffect(() => { load().catch((e) => setMessage(e.message)) }, [])

  function edit(post) { setForm(post); setMessage('') }

  async function save(publish = false) {
    setBusy(true)
    setMessage('')
    try {
      const body = { ...form, status: publish ? 'published' : form.status }
      const method = form.id ? 'PUT' : 'POST'
      const url = form.id ? `/api/v1/blog/${form.id}` : '/api/v1/blog'
      const r = await fetch(url, { method, headers: authHeaders(), body: JSON.stringify(body) })
      const data = await r.json()
      if (!r.ok) throw new Error(data.detail || `Save failed (${r.status})`)
      setForm(data)
      await load()
      setMessage(publish ? 'Published.' : 'Draft saved.')
    } catch (e) {
      setMessage(e.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove(id) {
    if (!window.confirm('Delete this post?')) return
    const r = await fetch(`/api/v1/blog/${id}`, { method: 'DELETE', headers: authHeaders() })
    if (!r.ok) {
      const data = await r.json().catch(() => ({}))
      setMessage(data.detail || 'Delete failed')
      return
    }
    setForm(EMPTY)
    await load()
  }

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 20px 80px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Blog editor</h1>
      <p style={{ color: '#64748b' }}>Create drafts, edit posts, publish or unpublish content.</p>
      {message && <p>{message}</p>}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px, 0.8fr) minmax(420px, 1.4fr)', gap: 24 }}>
        <section>
          <button onClick={() => setForm(EMPTY)} style={{ marginBottom: 12 }}>New post</button>
          {posts.map((post) => (
            <div key={post.id} style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <strong>{post.title}</strong>
              <div style={{ fontSize: 12, color: '#64748b' }}>{post.status} · {post.slug}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                <button onClick={() => edit(post)}>Edit</button>
                <button onClick={() => remove(post.id)}>Delete</button>
              </div>
            </div>
          ))}
        </section>
        <section>
          {['title', 'slug', 'excerpt', 'cover_image'].map((field) => (
            <label key={field} style={{ display: 'block', marginBottom: 12 }}>
              <div style={{ marginBottom: 4, textTransform: 'capitalize' }}>{field.replace('_', ' ')}</div>
              <input value={form[field] || ''} onChange={(e) => setForm({ ...form, [field]: e.target.value })} style={{ width: '100%', boxSizing: 'border-box', padding: 8 }} />
            </label>
          ))}
          <label style={{ display: 'block', marginBottom: 12 }}>
            <div style={{ marginBottom: 4 }}>Content</div>
            <textarea value={form.content || ''} onChange={(e) => setForm({ ...form, content: e.target.value })} rows={18} style={{ width: '100%', boxSizing: 'border-box', padding: 8, fontFamily: 'inherit' }} />
          </label>
          <label style={{ display: 'block', marginBottom: 16 }}>
            <input type="checkbox" checked={form.status === 'published'} onChange={(e) => setForm({ ...form, status: e.target.checked ? 'published' : 'draft' })} /> Published
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button disabled={busy} onClick={() => save(false)}>Save draft</button>
            <button disabled={busy} onClick={() => save(true)}>Publish</button>
          </div>
        </section>
      </div>
    </main>
  )
}
