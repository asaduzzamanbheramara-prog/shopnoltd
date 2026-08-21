const SERVICES = [
  {
    icon: '🌐',
    name: 'Domain Registration',
    description: 'Register and manage your Shopnoltd domains.',
    url: '/register',
  },
  {
    icon: '📋',
    name: 'ShopnoltdToolbox',
    description: 'ShopnoltdToolbox-powered data collection.',
    url: 'https://kobotoolbox.shopnoltd.dpdns.org',
  },
  {
    icon: '💬',
    name: 'Chat',
    description: 'Team and customer conversations.',
    url: 'https://chat.shopnoltd.dpdns.org',
  },
  {
    icon: '📹',
    name: 'Meet',
    description: 'Video conferencing.',
    url: 'https://meet.shopnoltd.dpdns.org',
  },
  {
    icon: '🔴',
    name: 'Live',
    description: 'Self-hosted live streaming.',
    url: 'https://live.shopnoltd.dpdns.org',
  },
  {
    icon: '🤖',
    name: 'AI',
    description: 'Shopnoltd AI tools.',
    url: 'https://ai.shopnoltd.dpdns.org',
  },
  {
    icon: '🧠',
    name: 'OpenAI',
    description: 'AI workspace.',
    url: 'https://openai.shopnoltd.dpdns.org',
  },
  {
    icon: '☁️',
    name: 'Mail',
    description: 'Shopnoltd mail services.',
    url: 'https://mail.shopnoltd.dpdns.org',
  },
  {
    icon: '💳',
    name: 'Billing',
    description: 'Billing and subscriptions.',
    url: 'https://billing.shopnoltd.dpdns.org',
  },
  {
    icon: '💻',
    name: 'Code Server',
    description: 'Browser-based development environment.',
    url: 'https://codeserver.shopnoltd.dpdns.org',
  },
  {
    icon: '📊',
    name: 'Monitoring',
    description: 'Platform monitoring and dashboards.',
    url: 'https://monitoring.shopnoltd.dpdns.org',
  },
  {
    icon: '🔌',
    name: 'API',
    description: 'Shopnoltd platform API.',
    url: 'https://api.shopnoltd.dpdns.org',
  },
]

export default function Services() {
  return (
    <main
      style={{
        maxWidth: 1200,
        margin: '0 auto',
        padding: '48px 24px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Shopnoltd Services</h1>

      <p style={{ color: '#64748b', fontSize: 18 }}>
        All Shopnoltd services in one place.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 18,
          marginTop: 32,
        }}
      >
        {SERVICES.map((service) => (
          <a
            key={service.name}
            href={service.url}
            target="_blank"
            rel="noreferrer"
            style={{
              textDecoration: 'none',
              color: 'inherit',
              border: '1px solid #e2e8f0',
              borderRadius: 14,
              padding: 24,
              background: 'white',
              boxShadow: '0 2px 8px rgba(15, 23, 42, 0.06)',
            }}
          >
            <div style={{ fontSize: 34 }}>{service.icon}</div>

            <h2 style={{ margin: '12px 0 8px' }}>
              {service.name}
            </h2>

            <p style={{ color: '#64748b', minHeight: 48 }}>
              {service.description}
            </p>

            <span style={{ color: '#0284c7', fontWeight: 600 }}>
              Open service →
            </span>
          </a>
        ))}
      </div>
    </main>
  )
}
