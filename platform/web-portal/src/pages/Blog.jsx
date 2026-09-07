import React from 'react'

const POSTS = [
  {
    title: 'Welcome to ShopnoltdToolbox',
    date: '2026-09-07',
    excerpt:
      'ShopnoltdToolbox brings domain registration, cloud and platform services, billing, payments, wallets, transactions and currency exchange together in one financial platform.',
  },
  {
    title: 'One Billing and Payment System for Every Service',
    date: '2026-09-07',
    excerpt:
      'Services use the same Shopnoltd financial layer for checkout, gateway selection, wallet balances, ledger entries, transactions and payment verification instead of separate service-specific payment logic.',
  },
  {
    title: 'Currency-Aware Pricing and Exchange',
    date: '2026-09-07',
    excerpt:
      'Displayed amounts and checkout amounts must follow the selected currency and the current Shopnoltd exchange rate. The original service price is preserved as the pricing source while conversion is calculated explicitly before payment.',
  },
  {
    title: 'Domain Registration Through ShopnoltdToolbox',
    date: '2026-09-07',
    excerpt:
      'Domain availability, registrar registration, billing authorization and payment are connected so a domain purchase is treated as a normal Shopnoltd service transaction.',
  },
  {
    title: 'Gateway and Payment Method Expansion',
    date: '2026-09-07',
    excerpt:
      'ShopnoltdToolbox maintains a broad gateway and payment-method catalogue while separating provider support, implementation, configuration, activation and live availability. Unsupported combinations are never presented as successful payments.',
  },
  {
    title: 'All Services, One Financial Center',
    date: '2026-09-07',
    excerpt:
      'Billing, checkout, payments, wallet, wallet ledger, transactions, subscriptions, invoices, reports and exchange are exposed through the unified financial API so new Shopnoltd services can reuse the same financial foundation.',
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
      <h1>ShopnoltdToolbox Blog</h1>
      <p style={{ color: '#64748b', marginBottom: 32 }}>
        Product updates, platform guides, domain services and financial-system news from ShopnoltdToolbox.
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
