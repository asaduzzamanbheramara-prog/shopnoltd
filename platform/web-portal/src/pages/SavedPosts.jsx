import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const shell = { maxWidth: 900, margin: '0 auto', padding: '28px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 12, background: '#fff' }

export default function SavedPosts() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true)
    setError('')
    try {
      const result = await platformApi.savedPosts()
      setPosts(Array.isArray(result) ? result : (result?.items || []))
    } catch (e) {
      setError(e.message || 'Saved posts could not be loaded.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [])

  return <main style={shell}>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
      <div><h1 style={{ marginBottom: 4 }}>Saved posts</h1><p style={{ color: '#64748b', marginTop: 0 }}>Posts you bookmarked for later.</p></div>
      <Link to="/feed">← Back to feed</Link>
    </div>
    {loading && <p>Loading saved posts…</p>}
    {error && <section role="alert" style={{ ...card, color: '#b91c1c' }}>{error} <button onClick={load}>Retry</button></section>}
    {!loading && !error && posts.length === 0 && <section style={card}>No saved posts yet. Use Save on a post to keep it here.</section>}
    {posts.map(post => <article key={post.id} style={card}>
      <div style={{ color: '#64748b', fontSize: 13, marginBottom: 8 }}>{post.user_id} · {post.published_at ? new Date(post.published_at).toLocaleString() : ''}</div>
      <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{post.content}</p>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', color: '#64748b', fontSize: 13 }}>
        <span>♥ {post.like_count || 0}</span><span>↗ {post.share_count || 0}</span><span>💬 {post.comment_count || 0}</span>
        <Link to={`/post/${post.id}`}>Open post →</Link>
        <button onClick={async () => { try { await platformApi.unsavePost(post.id); setPosts(current => current.filter(item => item.id !== post.id)) } catch (e) { setError(e.message) } }}>Remove saved</button>
      </div>
    </article>)}
  </main>
}
