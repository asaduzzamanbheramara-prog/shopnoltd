import React, { useEffect, useState } from 'react'

export default function Blog() {
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    fetch('/api/v1/blog?limit=50')
      .then(async (r) => {
        if (!r.ok) throw new Error(`Blog API returned ${r.status}`)
        return r.json()
      })
      .then((data) => {
        if (active) setPosts(Array.isArray(data) ? data : [])
      })
      .catch((e) => {
        if (active) setError(e.message || 'Unable to load blog posts')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <main
      style={{
        maxWidth: 900,
        margin: '0 auto',
        padding: '48px 20px 80px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Shopnoltd Blog</h1>
      <p style={{ color: '#64748b', marginBottom: 32 }}>
        Product updates, platform guides and service news from Shopnoltd.
      </p>

      {loading && <p>Loading posts…</p>}
      {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
      {!loading && !error && posts.length === 0 && (
        <p style={{ color: '#64748b' }}>No published posts yet.</p>
      )}

      <div style={{ display: 'grid', gap: 16 }}>
        {posts.map((post) => (
          <article
            key={post.id}
            style={{
              padding: 24,
              border: '1px solid #e2e8f0',
              borderRadius: 12,
              background: 'white',
            }}
          >
            {post.cover_image && (
              <img
                src={post.cover_image}
                alt=""
                loading="lazy"
                style={{ width: '100%', maxHeight: 320, objectFit: 'cover', borderRadius: 8 }}
              />
            )}
            <div style={{ color: '#64748b', fontSize: 13, marginTop: post.cover_image ? 16 : 0 }}>
              {post.published_at ? new Date(post.published_at).toLocaleDateString() : ''}
            </div>
            <h2 style={{ margin: '8px 0 10px' }}>{post.title}</h2>
            <p style={{ color: '#475569', lineHeight: 1.6 }}>
              {post.excerpt || post.content?.slice(0, 240)}
            </p>
          </article>
        ))}
      </div>
    </main>
  )
}
