import React, { useCallback, useEffect, useRef, useState } from 'react'
import { platformApi } from '../lib/platformApi'

const EMPTY = { id: null, title: '', slug: '', excerpt: '', content: '', cover_image: '', status: 'draft' }

export default function MyBlog() {
  const [posts, setPosts] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(true)
  const fileRef = useRef(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await platformApi.myBlog()
      setPosts(Array.isArray(data) ? data : [])
      setMessage('')
    } catch (e) {
      setPosts([])
      setMessage(`Unable to load My Blog: ${e?.message || 'request failed'}`)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  function editPost(post) {
    setMessage('')
    setForm({ ...EMPTY, ...post })
  }

  async function uploadCover(event) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true)
    setMessage('')
    try {
      const result = await platformApi.uploadBlogCover(file)
      setForm(prev => ({ ...prev, cover_image: result.url }))
      setMessage('Cover image uploaded. Save the post to keep it.')
    } catch (e) {
      setMessage(e?.message || 'Cover image upload failed.')
    } finally {
      setUploading(false)
    }
  }

  async function save(publish = false) {
    if (!form.title.trim() || !form.content.trim()) {
      setMessage('Title and content are required.')
      return
    }
    setBusy(true)
    setMessage('')
    const oldCover = form.id ? posts.find(p => p.id === form.id)?.cover_image : null
    try {
      const body = {
        title: form.title.trim(),
        slug: form.slug.trim() || null,
        excerpt: form.excerpt?.trim() || null,
        content: form.content,
        cover_image: form.cover_image || null,
        status: publish ? 'published' : 'draft',
      }
      const data = form.id
        ? await platformApi.updateBlogPost(form.id, body)
        : await platformApi.createBlogPost(body)
      setForm(data)
      await load()
      if (oldCover && oldCover !== data.cover_image) {
        await platformApi.deleteBlogCover(oldCover).catch(() => {})
      }
      setMessage(publish ? 'Published.' : 'Draft saved.')
    } catch (e) {
      setMessage(e?.message || 'Unable to save the post.')
    } finally {
      setBusy(false)
    }
  }

  async function togglePublish() {
    if (!form.id) return save(true)
    await save(form.status !== 'published')
  }

  async function remove(id) {
    const post = posts.find(p => p.id === id)
    if (!window.confirm('Delete this post permanently?')) return
    setBusy(true)
    setMessage('')
    try {
      await platformApi.deleteBlogPost(id)
      if (post?.cover_image) await platformApi.deleteBlogCover(post.cover_image).catch(() => {})
      setForm(EMPTY)
      await load()
      setMessage('Post deleted.')
    } catch (e) {
      setMessage(e?.message || 'Unable to delete the post.')
    } finally {
      setBusy(false)
    }
  }

  function newPost() {
    setMessage('')
    setForm(EMPTY)
  }

  return (
    <main style={{ maxWidth: 1200, margin: '0 auto', padding: '32px 20px 80px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>My Blog</h1>
      <p style={{ color: '#64748b' }}>Write, upload a cover image, save drafts, edit, publish/unpublish and delete your own posts.</p>
      {message && <div role="status" style={{ margin: '12px 0', padding: 10, borderRadius: 8, background: '#f1f5f9' }}>{message}</div>}
      <div style={{ marginBottom: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <button onClick={newPost} disabled={busy || uploading}>New post</button>
        <button onClick={load} disabled={busy || uploading || loading}>{loading ? 'Loading…' : 'Refresh'}</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(260px,.8fr) minmax(420px,1.4fr)', gap: 24 }}>
        <section>
          {loading && <p style={{ color: '#64748b' }}>Loading your posts…</p>}
          {!loading && posts.length === 0 && <p style={{ color: '#64748b' }}>No posts yet. Create your first draft.</p>}
          {!loading && posts.map(post => (
            <div key={post.id} style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: 12, marginBottom: 8 }}>
              {post.cover_image && <img src={post.cover_image} alt="" loading="lazy" style={{ width: '100%', height: 110, objectFit: 'cover', borderRadius: 6, marginBottom: 8 }} />}
              <strong>{post.title || 'Untitled'}</strong>
              <div style={{ fontSize: 12, color: '#64748b' }}>{post.status} · {post.slug}</div>
              <div style={{ marginTop: 8, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button onClick={() => editPost(post)} disabled={busy || uploading}>Edit</button>
                <button disabled={busy || uploading} onClick={() => remove(post.id)}>Delete</button>
              </div>
            </div>
          ))}
        </section>
        <section>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <div style={{ marginBottom: 4 }}>Title</div>
            <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} style={{ width: '100%', boxSizing: 'border-box', padding: 8 }} />
          </label>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <div style={{ marginBottom: 4 }}>Slug</div>
            <input value={form.slug} onChange={e => setForm({ ...form, slug: e.target.value })} placeholder="auto-generated from title" style={{ width: '100%', boxSizing: 'border-box', padding: 8 }} />
          </label>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <div style={{ marginBottom: 4 }}>Excerpt</div>
            <textarea value={form.excerpt || ''} onChange={e => setForm({ ...form, excerpt: e.target.value })} rows={3} style={{ width: '100%', boxSizing: 'border-box', padding: 8 }} />
          </label>
          <div style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 4 }}>Cover image</div>
            {form.cover_image && <img src={form.cover_image} alt="Cover preview" style={{ display: 'block', width: '100%', maxHeight: 260, objectFit: 'cover', borderRadius: 8, marginBottom: 8 }} />}
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,image/gif" onChange={uploadCover} disabled={uploading || busy} />
            <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>JPEG, PNG, WebP or GIF · maximum 8 MB</div>
            {form.cover_image && <button type="button" disabled={busy || uploading} onClick={() => setForm({ ...form, cover_image: '' })} style={{ marginTop: 8 }}>Remove cover</button>}
          </div>
          <label style={{ display: 'block', marginBottom: 12 }}>
            <div style={{ marginBottom: 4 }}>Content</div>
            <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} rows={18} style={{ width: '100%', boxSizing: 'border-box', padding: 8, fontFamily: 'inherit' }} />
          </label>
          <label style={{ display: 'block', marginBottom: 16 }}>
            <input type="checkbox" checked={form.status === 'published'} onChange={e => setForm({ ...form, status: e.target.checked ? 'published' : 'draft' })} /> Published
          </label>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button disabled={busy || uploading} onClick={() => save(false)}>Save draft</button>
            <button disabled={busy || uploading} onClick={() => save(true)}>Publish</button>
            {form.id && <button disabled={busy || uploading} onClick={togglePublish}>{form.status === 'published' ? 'Unpublish' : 'Publish'}</button>}
            {form.id && <button disabled={busy || uploading} onClick={() => remove(form.id)}>Delete</button>}
          </div>
        </section>
      </div>
    </main>
  )
}
