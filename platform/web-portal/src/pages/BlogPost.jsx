import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

function renderContentBlock(block, index) {
  const image = block.match(/^!\[([^\]]*)\]\((https:\/\/[^)\s]+)\)$/)
  if (image) {
    return <figure key={index} style={{ margin: '24px 0' }}>
      <img src={image[2]} alt={image[1]} loading="lazy" style={{ display: 'block', width: '100%', height: 'auto', maxHeight: 680, objectFit: 'contain', borderRadius: 12 }} />
      {image[1] && <figcaption style={{ color: '#64748b', fontSize: 14, marginTop: 8 }}>{image[1]}</figcaption>}
    </figure>
  }

  const video = block.match(/^\[VIDEO:\s*(https:\/\/[^\]]+)\]$/i)
  if (video) {
    try {
      const parsed = new URL(video[1].trim())
      const host = parsed.hostname.toLowerCase().replace(/^www\./, '')
      let id = ''
      if (host === 'youtu.be') id = parsed.pathname.split('/').filter(Boolean)[0] || ''
      else if (['youtube.com', 'm.youtube.com', 'youtube-nocookie.com'].includes(host)) {
        if (parsed.pathname === '/watch') id = parsed.searchParams.get('v') || ''
        else if (/^\/(embed|shorts)\//.test(parsed.pathname)) id = parsed.pathname.split('/')[2] || ''
      }
      if (parsed.protocol === 'https:' && /^[A-Za-z0-9_-]{11}$/.test(id)) {
        return <div key={index} style={{ position: 'relative', width: '100%', aspectRatio: '16 / 9', margin: '24px 0', overflow: 'hidden', borderRadius: 12 }}>
          <iframe title="Embedded YouTube video" src={`https://www.youtube-nocookie.com/embed/${id}`} loading="lazy" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0 }} allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen />
        </div>
      }
    } catch { /* Invalid video URLs are displayed as text below. */ }
  }

  return <p key={index} style={{ fontSize: 17, lineHeight: 1.85, color: '#475569', whiteSpace: 'pre-wrap' }}>{block}</p>
}

export default function BlogPost() {
  const { slug } = useParams()
  const [post, setPost] = useState(null)
  const [error, setError] = useState('')
  useEffect(() => { platformApi.blogPost(slug).then(setPost).catch(e => setError(e.message)) }, [slug])
  if (error || !post) return <main style={{ maxWidth: 850, margin: '0 auto', padding: '70px 20px', fontFamily: 'system-ui, sans-serif', textAlign: 'center' }}><h1>{error ? 'Article not found' : 'Loading…'}</h1>{error && <p style={{ color: '#64748b' }}>{error}</p>}<Link to="/blog">← Back to Blog</Link></main>
  const blocks = String(post.content || '').split(/\n\s*\n/).map(block => block.trim()).filter(Boolean)
  return <main style={{ maxWidth: 900, margin: '0 auto', padding: '42px 20px 80px', fontFamily: 'system-ui, sans-serif' }}>
    <Link to="/blog">← Back to Blog</Link>
    <article style={{ marginTop: 24 }}>
      {post.cover_image && <img src={post.cover_image} alt="" style={{ width: '100%', maxHeight: 430, objectFit: 'cover', borderRadius: 16 }} />}
      <div style={{ marginTop: 28 }}>
        <div style={{ color: '#0284c7', fontWeight: 700 }}>Shopnoltd Blog</div>
        <h1 style={{ fontSize: 'clamp(32px,5vw,52px)', margin: '8px 0 12px' }}>{post.title}</h1>
        <div style={{ color: '#64748b', marginBottom: 30 }}>{post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}</div>
        <p style={{ fontSize: 19, lineHeight: 1.8, color: '#334155', fontWeight: 600 }}>{post.excerpt}</p>
        {blocks.map(renderContentBlock)}
      </div>
    </article>
  </main>
}
