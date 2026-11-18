import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const actionStyle = { border: '1px solid #cbd5e1', background: '#fff', color: '#0f172a', borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontSize: 14 }

export default function BlogFeedCard({ post }) {
  const [like, setLike] = useState({ count: Number(post.like_count || 0), liked: false })
  const [shareCount, setShareCount] = useState(Number(post.share_count || 0))
  const [comments, setComments] = useState([])
  const [commentText, setCommentText] = useState('')
  const [busy, setBusy] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    Promise.all([
      platformApi.blogLikes(post.slug),
      platformApi.blogComments(post.slug),
      platformApi.blogShares(post.slug),
    ]).then(([likes, rows, shares]) => {
      if (!active) return
      setLike({ count: Number(likes?.count || 0), liked: Boolean(likes?.liked) })
      setComments(Array.isArray(rows) ? rows : [])
      setShareCount(Number(shares?.count || 0))
    }).catch(() => {})
    return () => { active = false }
  }, [post.slug])

  async function toggleLike() {
    setBusy(true); setMessage('')
    try {
      const result = like.liked ? await platformApi.unlikeBlog(post.slug) : await platformApi.likeBlog(post.slug)
      setLike({ count: Number(result?.count || 0), liked: Boolean(result?.liked) })
    } catch (error) { setMessage(error?.message || 'Sign in to like this article.') }
    finally { setBusy(false) }
  }

  async function shareArticle() {
    const url = new URL('/blog/' + encodeURIComponent(post.slug), window.location.origin).toString()
    try {
      if (navigator.share) await navigator.share({ title: post.title, text: post.excerpt || post.title, url })
      else if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(url)
      else { window.prompt('Copy this article link:', url); return }
    } catch (error) {
      if (error?.name !== 'AbortError') setMessage('Unable to share this article.')
      return
    }
    if (localStorage.getItem('shopno_token')) {
      try {
        const result = await platformApi.shareBlog(post.slug)
        setShareCount(Number(result?.count ?? shareCount))
      } catch { setMessage('Article shared; share count could not be recorded.') }
    }
  }

  async function submitComment(event) {
    event.preventDefault()
    const body = commentText.trim()
    if (!body) return
    setBusy(true); setMessage('')
    try {
      await platformApi.addBlogComment(post.slug, body)
      setCommentText('')
      const rows = await platformApi.blogComments(post.slug)
      setComments(Array.isArray(rows) ? rows : [])
      setExpanded(true)
      setMessage('Comment posted.')
    } catch (error) { setMessage(error?.message || 'Sign in to comment.') }
    finally { setBusy(false) }
  }

  return <article style={{ minWidth: 0, boxSizing: 'border-box', background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14, overflowWrap: 'anywhere' }}>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center', color: '#64748b', fontSize: 13, marginBottom: 10 }}>
      <b style={{ color: '#0f172a' }}>Shopnoltd Blog</b><span>·</span><span>{post.published_at ? new Date(post.published_at).toLocaleString() : 'Published article'}</span>
      {post.category && <span>· {post.category}</span>}
    </div>
    <h2 style={{ margin: '0 0 10px', fontSize: 23, lineHeight: 1.3 }}><Link to={'/blog/' + encodeURIComponent(post.slug)} style={{ color: '#0f172a', textDecoration: 'none' }}>{post.title}</Link></h2>
    <div aria-label="Article actions" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '0 0 14px' }}>
      <button type="button" disabled={busy} onClick={toggleLike} style={{ ...actionStyle, background: like.liked ? '#e0f2fe' : '#fff', borderColor: like.liked ? '#0284c7' : '#cbd5e1' }}>{like.liked ? '♥ Liked' : '♡ Like'} · {like.count}</button>
      <button type="button" onClick={() => setExpanded(value => !value)} style={actionStyle}>Comment · {comments.length}</button>
      <button type="button" onClick={shareArticle} style={actionStyle}>↗ Share · {shareCount}</button>
    </div>
    {post.cover_image && <Link to={'/blog/' + encodeURIComponent(post.slug)}><img src={post.cover_image} alt="" loading="lazy" style={{ display: 'block', width: '100%', maxHeight: 420, objectFit: 'cover', borderRadius: 10, marginBottom: 12 }} /></Link>}
    <p style={{ color: '#475569', lineHeight: 1.7, whiteSpace: 'pre-wrap', margin: '0 0 12px' }}>{post.excerpt || String(post.content || '').slice(0, 280)}</p>
    <Link to={'/blog/' + encodeURIComponent(post.slug)} style={{ color: '#0369a1', fontWeight: 700 }}>Read article →</Link>
    {expanded && <section style={{ marginTop: 16, borderTop: '1px solid #e2e8f0', paddingTop: 14 }}>
      <form onSubmit={submitComment} style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input value={commentText} onChange={event => setCommentText(event.target.value)} maxLength={2000} placeholder="Write a comment…" aria-label="Write a comment" style={{ flex: '1 1 220px', minWidth: 0, padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }} />
        <button type="submit" disabled={busy || !commentText.trim()} style={actionStyle}>Post comment</button>
      </form>
      {comments.slice(-5).map(comment => <div key={comment.id} style={{ padding: '10px 0', borderBottom: '1px solid #f1f5f9' }}><div style={{ color: '#64748b', fontSize: 12 }}>{comment.created_at ? new Date(comment.created_at).toLocaleString() : 'Comment'}</div><p style={{ margin: '4px 0', whiteSpace: 'pre-wrap' }}>{comment.body}</p></div>)}
    </section>}
    {message && <p role="status" style={{ color: '#64748b', fontSize: 13, marginBottom: 0 }}>{message}</p>}
  </article>
}
