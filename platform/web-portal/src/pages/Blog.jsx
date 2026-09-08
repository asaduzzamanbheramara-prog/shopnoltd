import React, { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

export const BLOG_POSTS = [
  {
    slug: 'welcome-to-shopnoltd',
    title: 'Welcome to Shopnoltd',
    date: '2026-09-06',
    category: 'Platform',
    author: 'Shopnoltd',
    image:
      'https://images.unsplash.com/photo-1556761175-b413da4baf72?auto=format&fit=crop&w=1200&q=80',
    excerpt:
      'Shopnoltd brings domains, cloud services, billing, payments, exchange, AI and collaboration tools together in one platform.',
    content: [
      'Shopnoltd is being built as a unified platform for domains, cloud services, billing, payments, AI and collaboration.',
      'The goal is to give customers one account, one dashboard and one place to manage the services they use.',
      'The platform is designed so individual services can evolve independently while remaining connected through shared identity, billing and service infrastructure.',
    ],
  },
  {
    slug: 'shopnoltd-billing-and-wallet',
    title: 'Shopnoltd Billing and Wallet',
    date: '2026-09-06',
    category: 'Billing',
    author: 'Shopnoltd',
    image:
      'https://images.unsplash.com/photo-1554224155-6726b3ff858f?auto=format&fit=crop&w=1200&q=80',
    excerpt:
      'Learn how wallet balances, transactions, billing gateways and checkout work together across the platform.',
    content: [
      'The Shopnoltd financial center brings billing, checkout, payment gateways, transactions, wallets and exchange functionality into one user-facing area.',
      'Wallet balances and ledger entries provide a transparent record of financial activity.',
      'Payment gateway support is designed around a capability-based architecture so additional providers can be activated without redesigning the customer experience.',
    ],
  },
  {
    slug: 'shopnoltd-platform-services',
    title: 'Shopnoltd Platform Services',
    date: '2026-09-06',
    category: 'Services',
    author: 'Shopnoltd',
    image:
      'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    excerpt:
      'Explore the services available from the Shopnoltd dashboard and service catalog.',
    content: [
      'Shopnoltd provides a growing catalog of platform services through the web portal.',
      'Services are exposed through common navigation, authentication and tenant-aware infrastructure.',
      'The service catalog is intended to make new capabilities discoverable without requiring customers to understand the underlying Kubernetes or microservice architecture.',
    ],
  },
]

export default function Blog() {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')

  const categories = useMemo(
    () => ['All', ...Array.from(new Set(BLOG_POSTS.map((post) => post.category)))],
    []
  )

  const posts = useMemo(() => {
    const q = query.trim().toLowerCase()

    return BLOG_POSTS.filter((post) => {
      const categoryMatch = category === 'All' || post.category === category
      const text = `${post.title} ${post.excerpt} ${post.category}`.toLowerCase()
      return categoryMatch && (!q || text.includes(q))
    })
  }, [query, category])

  const featured = BLOG_POSTS[0]

  return (
    <main
      style={{
        maxWidth: 1100,
        margin: '0 auto',
        padding: '42px 20px 80px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <header style={{ marginBottom: 28 }}>
        <div
          style={{
            color: '#0284c7',
            fontSize: 13,
            fontWeight: 800,
            letterSpacing: '.08em',
            textTransform: 'uppercase',
          }}
        >
          Shopnoltd
        </div>

        <h1 style={{ margin: '8px 0' }}>Blog</h1>

        <p style={{ color: '#64748b', maxWidth: 720, lineHeight: 1.7 }}>
          Product updates, platform guides and service news from Shopnoltd.
        </p>
      </header>

      <section
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 20,
          marginBottom: 36,
        }}
      >
        <Link
          to={`/blog/${featured.slug}`}
          style={{
            gridColumn: '1 / -1',
            display: 'grid',
            gridTemplateColumns: 'minmax(240px, .9fr) minmax(280px, 1.1fr)',
            textDecoration: 'none',
            color: 'inherit',
            border: '1px solid #e2e8f0',
            borderRadius: 16,
            overflow: 'hidden',
            background: '#fff',
          }}
        >
          <img
            src={featured.image}
            alt=""
            style={{
              width: '100%',
              height: '100%',
              minHeight: 250,
              objectFit: 'cover',
            }}
          />

          <div style={{ padding: 28 }}>
            <div
              style={{
                color: '#0284c7',
                fontSize: 13,
                fontWeight: 700,
                marginBottom: 8,
              }}
            >
              Featured · {featured.category}
            </div>

            <h2 style={{ margin: '0 0 12px' }}>{featured.title}</h2>

            <p style={{ color: '#475569', lineHeight: 1.7 }}>
              {featured.excerpt}
            </p>

            <span style={{ color: '#0284c7', fontWeight: 700 }}>
              Read article →
            </span>
          </div>
        </Link>
      </section>

      <section style={{ marginBottom: 28 }}>
        <div
          style={{
            display: 'flex',
            gap: 10,
            flexWrap: 'wrap',
            marginBottom: 14,
          }}
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search articles…"
            aria-label="Search articles"
            style={{
              flex: '1 1 240px',
              padding: 11,
              border: '1px solid #cbd5e1',
              borderRadius: 9,
            }}
          />

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            aria-label="Filter by category"
            style={{
              padding: 11,
              border: '1px solid #cbd5e1',
              borderRadius: 9,
            }}
          >
            {categories.map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </div>
      </section>

      {posts.length === 0 ? (
        <div
          style={{
            padding: 30,
            textAlign: 'center',
            border: '1px solid #e2e8f0',
            borderRadius: 12,
            color: '#64748b',
          }}
        >
          No articles match your search.
        </div>
      ) : (
        <section
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 18,
          }}
        >
          {posts.map((post) => (
            <article
              key={post.slug}
              style={{
                border: '1px solid #e2e8f0',
                borderRadius: 14,
                overflow: 'hidden',
                background: '#fff',
              }}
            >
              <Link
                to={`/blog/${post.slug}`}
                style={{ textDecoration: 'none', color: 'inherit' }}
              >
                <img
                  src={post.image}
                  alt=""
                  loading="lazy"
                  style={{
                    width: '100%',
                    height: 180,
                    objectFit: 'cover',
                    display: 'block',
                  }}
                />

                <div style={{ padding: 20 }}>
                  <div style={{ color: '#64748b', fontSize: 13 }}>
                    {post.date} · {post.category}
                  </div>

                  <h2 style={{ margin: '8px 0 10px', fontSize: 21 }}>
                    {post.title}
                  </h2>

                  <p style={{ color: '#475569', lineHeight: 1.6 }}>
                    {post.excerpt}
                  </p>

                  <span style={{ color: '#0284c7', fontWeight: 700 }}>
                    Read more →
                  </span>
                </div>
              </Link>
            </article>
          ))}
        </section>
      )}
    </main>
  )
}
