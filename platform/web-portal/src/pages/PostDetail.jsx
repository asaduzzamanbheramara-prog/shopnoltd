import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

export default function PostDetail() {
  const { id } = useParams()
  const [post, setPost] = useState(null)
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')
  const [liked, setLiked] = useState(false)
  const [saved, setSaved] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    platformApi.view(id).catch(() => {})
    Promise.all([
      platformApi.post ? platformApi.post(id) : fetch(`/api/v2/social/posts/${id}`).then(async r => {
        if (!r.ok) throw new Error(`Post request failed (HTTP ${r.status})`)
        return r.json()
      }),
      platformApi.comments(id),
      platformApi.isLiked(id),
      platformApi.isSaved(id),
    ])
      .then(([p, c, likeState, saveState]) => {
        setPost(p)
        setComments(c || [])
        setLiked(Boolean(likeState?.liked))
        setSaved(Boolean(saveState?.saved))
      })
      .catch(e => setError(e.message))
  }, [id])

  async function toggleLike() {
    setBusy(true)
    try {
      const result = liked ? await platformApi.unlike(id) : await platformApi.like(id)
      setLiked(!liked)
      setPost(current => current ? { ...current, like_count: result?.like_count ?? current.like_count } : current)
    } catch (e) { alert(e.message) } finally { setBusy(false) }
  }

  async function toggleSave() {
    setBusy(true)
    try {
      const result = saved ? await platformApi.unsavePost(id) : await platformApi.savePost(id)
      setSaved(Boolean(result?.saved))
    } catch (e) { alert(e.message) } finally { setBusy(false) }
  }

  async function sharePost() {
    const url = `${window.location.origin}/post/${id}`
    try {
      if (navigator.share) {
        await navigator.share({ title: 'Shopnoltd post', text: post?.content?.slice(0, 180) || '', url })
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(url)
      } else {
        throw new Error('Sharing is not available in this browser')
      }
      const result = await platformApi.share(id, 'copy')
      setPost(current => current ? { ...current, share_count: result?.share_count ?? current.share_count } : current)
    } catch (e) {
      if (e?.name !== 'AbortError') alert(e.message || 'Unable to share this post.')
    }
  }

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
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', marginTop: 12 }}>
        <button type="button" disabled={busy} onClick={toggleLike}>{liked ? '♥ Liked' : '♡ Like'} · {post.like_count || 0}</button>
        <button type="button" disabled={busy} onClick={sharePost}>↗ Share · {post.share_count || 0}</button>
        <button type="button" disabled={busy} onClick={toggleSave}>{saved ? '🔖 Saved' : '🔖 Save'}</button>
        <span style={{ color: '#64748b' }}>💬 {post.comment_count || comments.length}</span>
      </div>
      <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginTop: 18 }}>
        <input value={comment} onChange={e => setComment(e.target.value)} placeholder="Add a comment…" style={{ flex: 1, padding: 10 }} />
        <button>Comment</button>
      </form>
      {comments.map(c => <div key={c.id} style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid #e2e8f0' }}><b>{c.user_id}</b>: {c.body}</div>)}
    </article>
  </main>
}
