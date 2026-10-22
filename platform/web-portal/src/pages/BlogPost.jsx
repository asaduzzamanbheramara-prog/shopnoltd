import React, { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'
import { AdsterraResponsiveBanner } from '../components/AdsterraAds'

const buttonStyle = { border: '1px solid #cbd5e1', background: '#fff', color: '#0f172a', borderRadius: 8, padding: '9px 14px', cursor: 'pointer', fontSize: 14 }

function youtubeEmbedId(raw) {
  try {
    const parsed = new URL(raw.trim())
    const host = parsed.hostname.toLowerCase().replace(/^www\./, '')
    let id = ''
    if (host === 'youtu.be') id = parsed.pathname.split('/').filter(Boolean)[0] || ''
    else if (['youtube.com', 'm.youtube.com', 'youtube-nocookie.com'].includes(host)) {
      if (parsed.pathname === '/watch') id = parsed.searchParams.get('v') || ''
      else if (/^\/(embed|shorts)\//.test(parsed.pathname)) id = parsed.pathname.split('/')[2] || ''
    }
    return parsed.protocol === 'https:' && /^[A-Za-z0-9_-]{11}$/.test(id) ? id : ''
  } catch { return '' }
}

function renderContentBlock(block, index) {
  const image = block.match(/^!\[([^\]]*)\]\((https:\/\/[^)\s]+)\)$/)
  if (image) return <figure key={index} style={{ margin: '28px 0' }}>
    <img src={image[2]} alt={image[1]} loading="lazy" style={{ display: 'block', width: '100%', height: 'auto', maxHeight: 680, objectFit: 'contain', borderRadius: 12 }} />
    {image[1] && <figcaption style={{ color: '#64748b', fontSize: 14, marginTop: 8 }}>{image[1]}</figcaption>}
  </figure>

  const video = block.match(/^\[VIDEO:\s*(https:\/\/[^\]]+)\]$/i)
  if (video) {
    const id = youtubeEmbedId(video[1])
    if (id) return <div key={index} style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9', margin: '28px 0', overflow: 'hidden', borderRadius: 12, background: '#0f172a' }}>
      <iframe title="Embedded YouTube video" src={`https://www.youtube-nocookie.com/embed/${id}`} loading="lazy" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0 }} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen />
    </div>
  }

  if (/^#{1,3}\s+/.test(block)) {
    const level = Math.min(3, (block.match(/^#+/) || ['##'])[0].length)
    const heading = block.replace(/^#{1,6}\s+/, '')
    const Heading = `h${level}`
    return <Heading key={index} style={{ color: '#0f172a', lineHeight: 1.3, margin: '30px 0 12px' }}>{heading}</Heading>
  }
  if (/^[-*]\s+/.test(block)) return <ul key={index} style={{ paddingLeft: 28, lineHeight: 1.85, color: '#475569', fontSize: 17, margin: '12px 0 22px' }}>{block.split('\n').filter(Boolean).map((line, i) => <li key={i}>{line.replace(/^[-*]\s+/, '')}</li>)}</ul>
  return <p key={index} style={{ fontSize: 17, lineHeight: 1.85, color: '#475569', whiteSpace: 'pre-wrap', margin: '0 0 20px' }}>{block}</p>
}

export default function BlogPost() {
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [error, setError] = useState('')
  const [like, setLike] = useState({ count: 0, liked: false })
  const [comments, setComments] = useState([])
  const [commentText, setCommentText] = useState('')
  const [interactionMessage, setInteractionMessage] = useState('')
  const [interactionBusy, setInteractionBusy] = useState(false)

  const loadInteractions = useCallback(async () => {
    if (!slug) return
    try {
      const [likes, rows] = await Promise.all([platformApi.blogLikes(slug), platformApi.blogComments(slug)])
      setLike({ count: Number(likes?.count || 0), liked: Boolean(likes?.liked) })
      setComments(Array.isArray(rows) ? rows : [])
    } catch (e) {
      setInteractionMessage(e?.message || 'Could not load article interactions.')
    }
  }, [slug])

  useEffect(() => {
    let active = true
    platformApi.blogPost(slug).then(data => { if (active) setPost(data) }).catch(e => { if (active) setError(e.message) })
    loadInteractions()
    return () => { active = false }
  }, [slug, loadInteractions])

  const toggleLike = async () => {
    setInteractionBusy(true); setInteractionMessage('')
    try {
      const result = like.liked ? await platformApi.unlikeBlog(slug) : await platformApi.likeBlog(slug)
      setLike({ count: Number(result?.count || 0), liked: Boolean(result?.liked) })
    } catch (e) {
      setInteractionMessage(e?.message || 'Please sign in to like this article.')
    } finally { setInteractionBusy(false) }
  }

  const submitComment = async (event) => {
    event.preventDefault()
    const body = commentText.trim()
    if (!body) return
    setInteractionBusy(true); setInteractionMessage('')
    try {
      await platformApi.addBlogComment(slug, body)
      setCommentText('')
      await loadInteractions()
      setInteractionMessage('Comment posted.')
    } catch (e) {
      setInteractionMessage(e?.message || 'Please sign in to comment.')
    } finally { setInteractionBusy(false) }
  }

  const shareArticle = async () => {
    const url = window.location.href
    try {
      if (navigator.share) await navigator.share({ title: post.title, text: post.excerpt || post.title, url })
      else if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(url); setInteractionMessage('Article link copied.') }
      else { window.prompt('Copy this article link:', url); return }
    } catch (e) {
      if (e?.name !== 'AbortError') setInteractionMessage('Unable to share this article from this browser.')
    }
  }

  if (error || !post) return <main style={{ maxWidth: 850, margin: '0 auto', padding: '70px 20px', fontFamily: 'system-ui, sans-serif', textAlign: 'center' }}><h1>{error ? 'Article not found' : 'Loading…'}</h1>{error && <p style={{ color: '#64748b' }}>{error}</p>}<Link to="/blog">← Back to Blog</Link></main>

  // Split media markers into standalone blocks even when a draft saved one next to paragraph text.
  const normalizedContent = String(post.content || '')
    .replace(/\s*(\[VIDEO:\s*https:\/\/[^\]]+\])/gi, '\n\n$1\n\n')
    .replace(/\s*(!\[[^\]]*\]\(https:\/\/[^)\s]+\))/g, '\n\n$1\n\n')
  const blocks = normalizedContent.split(/\n\s*\n/).map(block => block.trim()).filter(Boolean)

  return <main style={{ width: '100%', maxWidth: 900, minWidth: 0, boxSizing: 'border-box', margin: '0 auto', padding: 'clamp(24px,5vw,42px) clamp(14px,4vw,20px) 80px', overflowWrap: 'anywhere', fontFamily: 'system-ui, sans-serif' }}>
    <Link to="/blog">← Back to Blog</Link>
    <article style={{ marginTop: 24 }}>
      {post.cover_image && <img src={post.cover_image} alt="" style={{ display: 'block', width: '100%', maxWidth: '100%', height: 'auto', maxHeight: 430, objectFit: 'cover', borderRadius: 16 }} />}
      <div style={{ marginTop: 28 }}>
        <div style={{ color: '#0284c7', fontWeight: 700 }}>Shopnoltd Blog</div>
        <h1 style={{ fontSize: 'clamp(32px,5vw,52px)', lineHeight: 1.15, margin: '8px 0 12px', color: '#0f172a' }}>{post.title}</h1>
        <div style={{ color: '#64748b', marginBottom: 30 }}>{post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}</div>
        {post.excerpt && <p style={{ fontSize: 19, lineHeight: 1.8, color: '#334155', fontWeight: 600, marginBottom: 28 }}>{post.excerpt}</p>}
        {blocks.map((block, index) => <React.Fragment key={index}>{renderContentBlock(block, index)}{index === 3 && blocks.length > 5 && <AdsterraResponsiveBanner />}</React.Fragment>)}
      </div>
      <section aria-label="Article actions" style={{ borderTop: '1px solid #e2e8f0', borderBottom: '1px solid #e2e8f0', padding: '18px 0', marginTop: 34, display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <button type="button" style={{ ...buttonStyle, background: like.liked ? '#e0f2fe' : '#fff', borderColor: like.liked ? '#0284c7' : '#cbd5e1' }} onClick={toggleLike} disabled={interactionBusy}>{like.liked ? '♥ Liked' : '♡ Like'} · {like.count}</button>
        <button type="button" style={buttonStyle} onClick={() => document.getElementById('blog-comments')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>Comment · {comments.length}</button>
        <button type="button" style={buttonStyle} onClick={shareArticle}>Share</button>
      </section>
      {interactionMessage && <p role="status" style={{ color: '#475569', fontSize: 14, margin: '12px 0' }}>{interactionMessage}</p>}
      <section id="blog-comments" style={{ marginTop: 34 }}>
        <h2 style={{ color: '#0f172a', fontSize: 25 }}>Comments ({comments.length})</h2>
        <form onSubmit={submitComment} style={{ display: 'grid', gap: 10, margin: '18px 0 28px' }}>
          <label htmlFor="blog-comment-input" style={{ fontWeight: 600 }}>Join the discussion</label>
          <textarea id="blog-comment-input" value={commentText} onChange={e => setCommentText(e.target.value)} maxLength={2000} rows={3} placeholder="Write a helpful comment…" style={{ width: '100%', boxSizing: 'border-box', border: '1px solid #cbd5e1', borderRadius: 8, padding: 12, font: 'inherit' }} />
          <div><button type="submit" style={{ ...buttonStyle, background: '#0f172a', color: '#fff' }} disabled={interactionBusy || !commentText.trim()}>Post comment</button></div>
          <small style={{ color: '#64748b' }}>You must be signed in to like or comment.</small>
        </form>
        {comments.length === 0 ? <p style={{ color: '#64748b' }}>No comments yet. Start the conversation.</p> : comments.map(comment => <article key={comment.id} style={{ borderTop: '1px solid #e2e8f0', padding: '16px 0' }}>
          <div style={{ color: '#64748b', fontSize: 13, marginBottom: 6 }}>{comment.created_at ? new Date(comment.created_at).toLocaleString() : 'Comment'}</div>
          <p style={{ margin: 0, lineHeight: 1.7, whiteSpace: 'pre-wrap', color: '#334155' }}>{comment.body}</p>
        </article>)}
      </section>
    </article>
  </main>
}
