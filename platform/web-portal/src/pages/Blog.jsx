import React, { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

const API_BASE = 'https://social-service.shopnoltd.dpdns.org/api/v1/blog'
const PAGE_SIZE = 9
const stripHtml = value => String(value || '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()

function PostCard({ post }) {
  return <article style={{ border: '1px solid #e2e8f0', borderRadius: 16, overflow: 'hidden', background: 'white', boxShadow: '0 3px 12px rgba(15,23,42,.05)' }}>
    {post.cover_image && <img src={post.cover_image} alt="" loading="lazy" style={{ width: '100%', height: 190, objectFit: 'cover' }} />}
    <div style={{ padding: 20 }}><div style={{ color: '#64748b', fontSize: 13 }}>{post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}</div><h2 style={{ fontSize: 21, margin: '8px 0 10px' }}>{post.title}</h2><p style={{ color: '#475569', lineHeight: 1.6 }}>{post.excerpt || stripHtml(post.content).slice(0, 220)}</p><Link to={`/blog/${encodeURIComponent(post.slug)}`} style={{ color: '#0369a1', fontWeight: 700, textDecoration: 'none' }}>Read article →</Link></div>
  </article>
}

function Article({ slug }) {
  const [post, setPost] = useState(null); const [error, setError] = useState(''); const [loading, setLoading] = useState(true)
  useEffect(() => { let active = true; setLoading(true); fetch(`${API_BASE}/${encodeURIComponent(slug)}`).then(async r => { if (!r.ok) throw new Error(r.status === 404 ? 'Article not found' : `Blog API returned ${r.status}`); return r.json() }).then(data => active && setPost(data)).catch(e => active && setError(e.message)).finally(() => active && setLoading(false)); return () => { active = false } }, [slug])
  if (loading) return <main style={page}>Loading article…</main>
  if (error || !post) return <main style={page}><Link to="/blog">← Back to blog</Link><h1 style={{ marginTop: 24 }}>{error || 'Article not found'}</h1></main>
  return <main style={{ ...page, maxWidth: 960 }}><Link to="/blog" style={{ color: '#0369a1', fontWeight: 700, textDecoration: 'none' }}>← Back to blog</Link>{post.cover_image && <img src={post.cover_image} alt="" style={{ width: '100%', maxHeight: 480, objectFit: 'cover', borderRadius: 18, marginTop: 20 }} />}<div style={{ color: '#64748b', marginTop: 24 }}>{post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}</div><h1 style={{ fontSize: 'clamp(34px,6vw,56px)', lineHeight: 1.08, margin: '10px 0 20px' }}>{post.title}</h1>{post.excerpt && <p style={{ fontSize: 19, color: '#475569', lineHeight: 1.7 }}>{post.excerpt}</p>}<article style={{ fontSize: 17, lineHeight: 1.85, color: '#1e293b', whiteSpace: 'pre-wrap' }}>{stripHtml(post.content)}</article></main>
}

const page = { maxWidth: 1100, margin: '0 auto', padding: 'clamp(28px,6vw,52px) clamp(14px,4vw,24px) 80px', fontFamily: 'system-ui,sans-serif' }

export default function Blog() {
  const { slug } = useParams()
  const [posts, setPosts] = useState([]); const [loading, setLoading] = useState(true); const [error, setError] = useState(''); const [query, setQuery] = useState(''); const [pageNo, setPageNo] = useState(1)
  useEffect(() => { if (slug) return; let active = true; setLoading(true); fetch(`${API_BASE}?limit=50`).then(async r => { if (!r.ok) throw new Error(`Blog API returned ${r.status}`); return r.json() }).then(data => active && setPosts(Array.isArray(data) ? data : [])).catch(e => active && setError(e.message || 'Unable to load blog posts')).finally(() => active && setLoading(false)); return () => { active = false } }, [slug])
  const filtered = useMemo(() => posts.filter(post => `${post.title} ${post.excerpt || ''} ${stripHtml(post.content)}`.toLowerCase().includes(query.toLowerCase())), [posts, query])
  const visible = filtered.slice((pageNo - 1) * PAGE_SIZE, pageNo * PAGE_SIZE)
  if (slug) return <Article slug={slug} />
  return <main style={page}><section style={{ padding: '28px clamp(20px,5vw,44px)', borderRadius: 20, background: 'linear-gradient(135deg,#0ea5e9,#0369a1)', color: 'white' }}><div style={{ fontSize: 38 }}>📰</div><h1 style={{ fontSize: 'clamp(34px,6vw,52px)', margin: '8px 0' }}>Shopnoltd Blog</h1><p style={{ lineHeight: 1.7, maxWidth: 760 }}>Product updates, platform guides, engineering notes and service news from Shopnoltd.</p></section><div style={{ margin: '24px 0', display: 'flex', gap: 10 }}><input value={query} onChange={e => { setQuery(e.target.value); setPageNo(1) }} placeholder="Search articles…" aria-label="Search blog" style={{ flex: 1, padding: 13, border: '1px solid #cbd5e1', borderRadius: 10, fontSize: 15 }} /></div>{loading && <p>Loading posts…</p>}{error && <p style={{ color: '#b91c1c' }}>{error}</p>}{!loading && !error && !filtered.length && <p style={{ color: '#64748b' }}>No published posts match your search.</p>}<div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18 }}>{visible.map(post => <PostCard key={post.id} post={post} />)}</div>{filtered.length > PAGE_SIZE && <nav aria-label="Blog pagination" style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 28, alignItems: 'center' }}><button disabled={pageNo === 1} onClick={() => setPageNo(n => n - 1)} style={button}>Previous</button><span style={{ color: '#64748b' }}>Page {pageNo} of {Math.ceil(filtered.length / PAGE_SIZE)}</span><button disabled={pageNo >= Math.ceil(filtered.length / PAGE_SIZE)} onClick={() => setPageNo(n => n + 1)} style={button}>Next</button></nav>}</main>
}

const button = { padding: '9px 14px', border: '1px solid #cbd5e1', borderRadius: 8, background: 'white', cursor: 'pointer' }
