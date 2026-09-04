import React from 'react'
import { Link } from 'react-router-dom'
import { BLOG_POSTS } from '../data/blogPosts'

export default function Blog() {
  return (
    <main
      style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px)',
        fontFamily: 'system-ui, sans-serif',
        boxSizing: 'border-box',
      }}
    >
      <header>
        <h1 style={{ marginBottom: 8 }}>Shopnoltd Blog</h1>
        <p style={{ color: '#64748b', fontSize: 18, lineHeight: 1.6 }}>
          Product updates, platform engineering and practical guides from Shopnoltd.
        </p>
      </header>

      <section
        aria-label="Blog posts"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
          gap: 20,
          marginTop: 32,
        }}
      >
        {BLOG_POSTS.map((post) => (
          <article
            key={post.slug}
            style={{
              border: '1px solid #e2e8f0',
              borderRadius: 14,
              padding: 22,
              background: '#fff',
              boxShadow: '0 2px 8px rgba(15, 23, 42, 0.06)',
            }}
          >
            <div style={{ color: '#0284c7', fontSize: 13, fontWeight: 700 }}>
              {post.category}
            </div>
            <h2 style={{ margin: '10px 0 8px', lineHeight: 1.25 }}>{post.title}</h2>
            <p style={{ color: '#64748b', lineHeight: 1.6 }}>{post.excerpt}</p>
            <p style={{ color: '#94a3b8', fontSize: 13 }}>
              {post.author} · {post.publishedAt}
            </p>
            <Link
              to={`/blog/${post.slug}`}
              style={{ color: '#0284c7', fontWeight: 700, textDecoration: 'none' }}
            >
              Read article →
            </Link>
          </article>
        ))}
      </section>
    </main>
  )
}
