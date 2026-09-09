import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

export default function Blog() {
  const [posts, setPosts] = useState([])
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await platformApi.blog()
      setPosts(Array.isArray(data) ? data : (data?.items || []))
    } catch (e) {
      const message = String(e?.message || e || 'Unable to load the public blog')
      setError(message === 'Not Found' ? 'The public blog API is unavailable. Please try again.' : message)
      setPosts([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const categories = useMemo(() => ['All', ...Array.from(new Set(posts.map(p => p.category || 'General')))], [posts])
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    return posts.filter(p => {
      const cat = p.category || 'General'
      return (category === 'All' || cat === category) && (!q || `${p.title} ${p.excerpt || ''} ${p.content || ''}`.toLowerCase().includes(q))
    })
  }, [posts, query, category])

  return <main style={{ maxWidth: 1100, margin: '0 auto', padding: '42px 20px 80px', fontFamily: 'system-ui, sans-serif' }}>
    <header>
      <div style={{ color: '#0284c7', fontWeight: 800 }}>SHOPNOLTD</div>
      <h1>Blog</h1>
      <p style={{ color: '#64748b' }}>Product updates, platform guides and service news from Shopnoltd.</p>
    </header>
    {error && <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', color: '#b91c1c', margin: '16px 0' }}><span>{error}</span><button type="button" onClick={load} disabled={loading}>Retry</button></div>}
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', margin: '24px 0' }}>
      <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search articles…" style={{ flex: '1 1 260px', padding: 11, border: '1px solid #cbd5e1', borderRadius: 9 }} />
      <select value={category} onChange={e => setCategory(e.target.value)} style={{ padding: 11, border: '1px solid #cbd5e1', borderRadius: 9 }}>{categories.map(c => <option key={c}>{c}</option>)}</select>
    </div>
    {loading ? <div style={{ padding: 30, border: '1px solid #e2e8f0', borderRadius: 12, color: '#64748b' }}>Loading published articles…</div> : filtered.length === 0 ? <div style={{ padding: 30, border: '1px solid #e2e8f0', borderRadius: 12, color: '#64748b' }}>{error ? 'The blog could not be loaded.' : 'No published articles match your search.'}</div> : <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18 }}>{filtered.map(p => <article key={p.id} style={{ border: '1px solid #e2e8f0', borderRadius: 14, overflow: 'hidden' }}>{p.cover_image && <img src={p.cover_image} alt="" loading="lazy" style={{ width: '100%', height: 180, objectFit: 'cover' }} />}<div style={{ padding: 20 }}><div style={{ color: '#64748b', fontSize: 13 }}>{p.published_at ? new Date(p.published_at).toLocaleDateString() : ''}</div><h2>{p.title}</h2><p style={{ color: '#475569', lineHeight: 1.6 }}>{p.excerpt || p.content?.slice(0, 180)}</p><Link to={`/blog/${p.slug}`}>Read more →</Link></div></article>)}</section>}
  </main>
}
