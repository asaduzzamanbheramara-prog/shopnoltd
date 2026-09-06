import React from 'react'

const POSTS = [
  {
    title: 'Welcome to Shopnoltd',
    date: '2026-09-06',
    excerpt:
      'Shopnoltd brings domains, cloud services, billing, payments, exchange, AI and collaboration tools together in one platform.',
  },
  {
    title: 'Shopnoltd Billing and Wallet',
    date: '2026-09-06',
    excerpt:
      'Learn how wallet balances, transactions, billing gateways and checkout work together across the platform.',
  },
  {
    title: 'Shopnoltd Platform Services',
    date: '2026-09-06',
    excerpt:
      'Explore the services available from the Shopnoltd dashboard and service catalog.',
  },
]

export default function Blog() {
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

      <div
        style={{
          display: 'grid',
          gap: 16,
        }}
      >
        {POSTS.map((post) => (
          <article
            key={post.title}
            style={{
              padding: 24,
              border: '1px solid #e2e8f0',
              borderRadius: 12,
              background: 'white',
            }}
          >
            <div style={{ color: '#64748b', fontSize: 13 }}>
              {post.date}
            </div>

            <h2 style={{ margin: '8px 0 10px' }}>
              {post.title}
            </h2>

            <p style={{ color: '#475569', lineHeight: 1.6 }}>
              {post.excerpt}
            </p>
          </article>
        ))}
      </div>
    </main>
  )
}
