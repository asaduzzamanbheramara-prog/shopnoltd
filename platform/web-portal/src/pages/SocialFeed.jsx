import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const shell = { maxWidth: 900, margin: '0 auto', padding: '28px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14 }

function PostCard({ post, refresh, following, toggleFollow }) {
  const navigate = useNavigate()
  const [liked, setLiked] = useState(false)
  const [comments, setComments] = useState([])
  const [comment, setComment] = useState('')
  const [busy, setBusy] = useState(false)
  const isFollowing = following.has(String(post.user_id))

  useEffect(() => {
    platformApi.view(post.id).catch(() => {})
    platformApi.comments(post.id).then(setComments).catch(() => {})
  }, [post.id])

  async function toggleLike() {
    setBusy(true)
    try {
      const data = liked ? await platformApi.unlike(post.id) : await platformApi.like(post.id)
      setLiked(!liked)
      refresh(post.id, data?.like_count)
    } catch (e) { alert(e.message) } finally { setBusy(false) }
  }

  async function doShare() {
    try { await platformApi.share(post.id); alert('Shared to your Shopnoltd feed.') } catch (e) { alert(e.message) }
  }

  async function addComment(e) {
    e.preventDefault()
    if (!comment.trim()) return
    try {
      await platformApi.comment(post.id, comment.trim())
      setComment('')
      setComments(await platformApi.comments(post.id))
      refresh(post.id, undefined, (post.comment_count || 0) + 1)
    } catch (e) { alert(e.message) }
  }

  const direct = `${window.location.origin}/post/${post.id}`
  return (
    <article style={card}>
      <div style={{ color: '#64748b', fontSize: 13, marginBottom: 10, display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
        <b style={{ color: '#0f172a' }}>{post.user_id}</b>
        {String(post.user_id) !== String(localStorage.getItem('shopno_user_id') || '') && (
          <button onClick={() => toggleFollow(post.user_id)} style={{ padding: '3px 8px' }}>
            {isFollowing ? 'Following' : 'Follow'}
          </button>
        )}
        · {post.published_at ? new Date(post.published_at).toLocaleString() : ''}
      </div>
      <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{post.content}</div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 16 }}>
        <button disabled={busy} onClick={toggleLike}>{liked ? '♥ Liked' : '♡ Like'} · {post.like_count || 0}</button>
        <button onClick={doShare}>↗ Share · {post.share_count || 0}</button>
        <button onClick={() => navigator.clipboard?.writeText(direct)}>🔗 Copy link</button>
        <button onClick={() => navigate(`/post/${post.id}`)}>Open</button>
      </div>
      <form onSubmit={addComment} style={{ display: 'flex', gap: 8, marginTop: 14 }}>
        <input value={comment} onChange={e => setComment(e.target.value)} placeholder="Write a comment…" style={{ flex: 1, padding: 9, border: '1px solid #cbd5e1', borderRadius: 8 }} />
        <button type="submit">Comment</button>
      </form>
      {comments.length > 0 && <div style={{ marginTop: 12, borderTop: '1px solid #e2e8f0', paddingTop: 10 }}>
        {comments.slice(-5).map(c => <div key={c.id} style={{ padding: '7px 0', fontSize: 14 }}><b>{c.user_id}</b>: {c.body}</div>)}
      </div>}
    </article>
  )
}

export default function SocialFeed() {
  const [posts, setPosts] = useState([])
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [following, setFollowing] = useState(new Set())

  const load = () => {
    setLoading(true)
    Promise.all([
      platformApi.globalFeed(),
      platformApi.following().catch(() => []),
    ]).then(([feed, followed]) => {
      setPosts(Array.isArray(feed) ? feed : (feed?.items || []))
      setFollowing(new Set((Array.isArray(followed) ? followed : []).map(String)))
    }).catch(e => setError(e.message)).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function create() {
    if (!content.trim()) return
    try { await platformApi.createPost(content.trim()); setContent(''); load() } catch (e) { alert(e.message) }
  }

  async function toggleFollow(userId) {
    const key = String(userId)
    try {
      if (following.has(key)) {
        await platformApi.unfollow(userId)
        setFollowing(current => { const next = new Set(current); next.delete(key); return next })
      } else {
        await platformApi.follow(userId)
        setFollowing(current => new Set(current).add(key))
      }
    } catch (e) { alert(e.message) }
  }

  function refresh(id, likeCount, commentCount) {
    setPosts(current => current.map(p => p.id === id ? { ...p, ...(likeCount !== undefined ? { like_count: likeCount } : {}), ...(commentCount !== undefined ? { comment_count: commentCount } : {}) } : p))
  }

  return <div style={shell}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
      <div><h1 style={{ marginBottom: 4 }}>Shopnoltd Feed</h1><p style={{ color: '#64748b', marginTop: 0 }}>Create, watch, like, comment, share and follow with direct post links.</p></div>
      <Link to="/work" style={{ padding: '9px 13px', background: '#0ea5e9', color: '#fff', borderRadius: 8, textDecoration: 'none', fontWeight: 700 }}>Find Work</Link>
    </div>
    <section style={card}>
      <textarea value={content} onChange={e => setContent(e.target.value)} rows={4} placeholder="What do you want to share?" style={{ width: '100%', boxSizing: 'border-box', padding: 12, borderRadius: 10, border: '1px solid #cbd5e1', resize: 'vertical' }} />
      <button onClick={create} style={{ marginTop: 10, padding: '9px 15px', border: 0, borderRadius: 8, background: '#0ea5e9', color: '#fff', fontWeight: 700 }}>Publish</button>
    </section>
    {loading && <p>Loading feed…</p>}
    {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
    {!loading && posts.length === 0 && <div style={card}>No posts yet. Be the first to publish.</div>}
    {posts.map(post => <PostCard key={post.id} post={post} refresh={refresh} following={following} toggleFollow={toggleFollow} />)}
  </div>
}
