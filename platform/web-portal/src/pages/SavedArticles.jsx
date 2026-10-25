import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const shell = { maxWidth: 1000, margin: '0 auto', padding: '28px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { minWidth: 0, border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14, background: '#fff' }

export default function SavedArticles() {
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const result = await platformApi.savedBlogs()
      setArticles(Array.isArray(result) ? result : (result?.items || []))
    } catch (e) {
      setError(e.message || 'Saved articles could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return <main style={shell}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
      <div><h1 style={{ marginBottom: 4 }}>Saved articles</h1><p style={{ color: '#64748b', marginTop: 0 }}>Blog posts you bookmarked for later.</p></div>
      <Link to="/blog">← Back to blog</Link>
    </div>
    {loading && <p>Loading saved articles…</p>}
    {error && <section role="alert" style={{ ...card, color: '#b91c1c' }}>{error} <button onClick={load}>Retry</button></section>}
    {!loading && !error && articles.length === 0 && <section style={card}>No saved articles yet. Use Save on a published article to keep it here.</section>}
    {articles.map(article => <article key={article.id} style={card}>
      {article.cover_image && <img src={article.cover_image} alt="" loading="lazy" style={{ display: 'block', width: '100%', maxHeight: 280, objectFit: 'cover', borderRadius: 10, marginBottom: 12 }} />}
      <div style={{ color: '#64748b', fontSize: 13 }}>{article.published_at ? new Date(article.published_at).toLocaleDateString() : ''}</div>
      <h2 style={{ overflowWrap: 'anywhere' }}>{article.title}</h2>
      <p style={{ color: '#475569', lineHeight: 1.6 }}>{article.excerpt || String(article.content || '').slice(0, 220)}</p>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <Link to={`/blog/${article.slug}`}>Read article →</Link>
        <button onClick={async () => { try { await platformApi.unsaveBlog(article.slug); setArticles(current => current.filter(item => item.id !== article.id)) } catch (e) { setError(e.message) } }}>Remove saved</button>
      </div>
    </article>)}
  </main>
}
