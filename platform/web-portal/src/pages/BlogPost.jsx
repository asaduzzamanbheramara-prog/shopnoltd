import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { getBlogPost } from '../data/blogPosts'

export default function BlogPost() {
  const { slug } = useParams()
  const post = getBlogPost(slug)

  if (!post) {
    return (
      <main style={{ maxWidth: 760, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
        <h1>Article not found</h1>
        <p style={{ color: '#64748b' }}>The requested blog article does not exist.</p>
        <Link to="/blog" style={{ color: '#0284c7', fontWeight: 700 }}>← Back to Blog</Link>
      </main>
    )
  }

  return (
    <main style={{ maxWidth: 800, margin: '0 auto', padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px)', fontFamily: 'system-ui, sans-serif' }}>
      <Link to="/blog" style={{ color: '#0284c7', textDecoration: 'none', fontWeight: 700 }}>← Blog</Link>
      <p style={{ color: '#0284c7', fontWeight: 700, marginTop: 28 }}>{post.category}</p>
      <h1 style={{ fontSize: 'clamp(32px, 6vw, 48px)', lineHeight: 1.15, margin: '8px 0 12px' }}>{post.title}</h1>
      <p style={{ color: '#64748b' }}>{post.author} · {post.publishedAt}</p>
      <p style={{ fontSize: 20, lineHeight: 1.6, color: '#475569', marginTop: 28 }}>{post.excerpt}</p>
      <div style={{ marginTop: 32 }}>
        {post.content.map((paragraph) => (
          <p key={paragraph} style={{ lineHeight: 1.8, fontSize: 17, color: '#334155' }}>{paragraph}</p>
        ))}
      </div>
    </main>
  )
}
