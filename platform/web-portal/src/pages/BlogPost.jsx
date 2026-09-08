import React, { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

export default function BlogPost() {
  const { slug } = useParams(); const [post, setPost] = useState(null); const [error, setError] = useState('')
  useEffect(() => { platformApi.blogPost(slug).then(setPost).catch(e => setError(e.message)) }, [slug])
  if (error || !post) return <main style={{ maxWidth: 850, margin: '0 auto', padding: '70px 20px', fontFamily: 'system-ui, sans-serif', textAlign: 'center' }}><h1>{error ? 'Article not found' : 'Loading…'}</h1>{error && <p style={{ color: '#64748b' }}>{error}</p>}<Link to="/blog">← Back to Blog</Link></main>
  return <main style={{ maxWidth: 900, margin: '0 auto', padding: '42px 20px 80px', fontFamily: 'system-ui, sans-serif' }}><Link to="/blog">← Back to Blog</Link><article style={{ marginTop: 24 }}>{post.cover_image && <img src={post.cover_image} alt="" style={{ width: '100%', maxHeight: 430, objectFit: 'cover', borderRadius: 16 }} />}<div style={{ marginTop: 28 }}><div style={{ color: '#0284c7', fontWeight: 700 }}>Shopnoltd Blog</div><h1 style={{ fontSize: 'clamp(32px,5vw,52px)', margin: '8px 0 12px' }}>{post.title}</h1><div style={{ color: '#64748b', marginBottom: 30 }}>{post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}</div><p style={{ fontSize: 19, lineHeight: 1.8, color: '#334155', fontWeight: 600 }}>{post.excerpt}</p>{String(post.content || '').split(/\n\s*\n/).filter(Boolean).map((paragraph, i) => <p key={i} style={{ fontSize: 17, lineHeight: 1.85, color: '#475569', whiteSpace: 'pre-wrap' }}>{paragraph}</p>)}</div></article></main>
}
