import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

export default function PostDetail() {
  const { id } = useParams()
  const [post, setPost] = useState(null)
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    platformApi.view(id).catch(() => {})
    Promise.all([platformApi.post ? platformApi.post(id) : fetch(`/api/v2/social/posts/${id}`).then(r => r.json()), platformApi.comments(id)])
      .then(([p, c]) => { setPost(p); setComments(c || []) })
      .catch(e => setError(e.message))
  }, [id])

  async function addComment(e) {
    e.preventDefault()
    if (!comment.trim()) return
    try {
      await platformApi.comment(id, comment.trim())
      setComment('')
      setComments(await platformApi.comments(id))
    } catch (e) { alert(e.message) }
  }

  if (error) return <div style={{ padding: 32 }}><h2>Post unavailable</h2><p>{error}</p><Link to="/feed">Back to feed</Link></div>
  if (!post) return <div style={{ padding: 32 }}>Loading post…</div>

  return <main style={{ maxWidth: 760, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui, sans-serif' }}>
    <Link to="/feed">← Feed</Link>
    <article style={{ marginTop: 18, padding: 22, border: '1px solid #e2e8f0', borderRadius: 14 }}>
      <div style={{ color: '#64748b', fontSize: 13 }}>{post.user_id} · {post.published_at ? new Date(post.published_at).toLocaleString() : ''}</div>
      <p style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7, fontSize: 18 }}>{post.content}</p>
      <div style={{ color: '#64748b' }}>♥ {post.like_count || 0} · ↗ {post.share_count || 0} · 💬 {post.comment_count || 0}</div>
      <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginTop: 18 }}>
        <input value={comment} onChange={e => setComment(e.target.value)} placeholder="Add a comment…" style={{ flex: 1, padding: 10 }} />
        <button>Comment</button>
      </form>
      {comments.map(c => <div key={c.id} style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #e2e8f0' }}><b>{c.user_id}</b>: {c.body}</div>)}
    </article>
  </main>
}
