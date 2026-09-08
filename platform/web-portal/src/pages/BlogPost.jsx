import React from 'react'
import { Link, useParams } from 'react-router-dom'
import { BLOG_POSTS } from './Blog'

export default function BlogPost() {
  const { slug } = useParams()
  const post = BLOG_POSTS.find((item) => item.slug === slug)

  if (!post) {
    return (
      <main
        style={{
          maxWidth: 850,
          margin: '0 auto',
          padding: '70px 20px',
          fontFamily: 'system-ui, sans-serif',
          textAlign: 'center',
        }}
      >
        <h1>Article not found</h1>
        <p style={{ color: '#64748b' }}>
          The article you requested does not exist or may have been removed.
        </p>
        <Link to="/blog">← Back to Blog</Link>
      </main>
    )
  }

  const related = BLOG_POSTS.filter(
    (item) => item.slug !== post.slug && item.category === post.category
  )

  return (
    <main
      style={{
        maxWidth: 900,
        margin: '0 auto',
        padding: '42px 20px 80px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <Link
        to="/blog"
        style={{
          color: '#0284c7',
          textDecoration: 'none',
          fontWeight: 700,
        }}
      >
        ← Back to Blog
      </Link>

      <article style={{ marginTop: 24 }}>
        <img
          src={post.image}
          alt=""
          style={{
            width: '100%',
            maxHeight: 430,
            objectFit: 'cover',
            borderRadius: 16,
            display: 'block',
          }}
        />

        <div style={{ marginTop: 28 }}>
          <div style={{ color: '#0284c7', fontWeight: 700 }}>
            {post.category}
          </div>

          <h1 style={{ fontSize: 'clamp(32px, 5vw, 52px)', margin: '8px 0 12px' }}>
            {post.title}
          </h1>

          <div style={{ color: '#64748b', marginBottom: 30 }}>
            {post.date} · {post.author}
          </div>

          <p
            style={{
              fontSize: 19,
              lineHeight: 1.8,
              color: '#334155',
              fontWeight: 600,
            }}
          >
            {post.excerpt}
          </p>

          {post.content.map((paragraph) => (
            <p
              key={paragraph}
              style={{
                fontSize: 17,
                lineHeight: 1.85,
                color: '#475569',
              }}
            >
              {paragraph}
            </p>
          ))}
        </div>
      </article>

      {related.length > 0 && (
        <section style={{ marginTop: 55 }}>
          <h2>Related articles</h2>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 14,
            }}
          >
            {related.map((item) => (
              <Link
                key={item.slug}
                to={`/blog/${item.slug}`}
                style={{
                  textDecoration: 'none',
                  color: 'inherit',
                  border: '1px solid #e2e8f0',
                  borderRadius: 12,
                  padding: 18,
                }}
              >
                <strong>{item.title}</strong>
                <p style={{ color: '#64748b', lineHeight: 1.5 }}>
                  {item.excerpt}
                </p>
              </Link>
            ))}
          </div>
        </section>
      )}
    </main>
  )
}
