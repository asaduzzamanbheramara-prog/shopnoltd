const SERVICES = [
  {
    icon: '🌐',
    name: 'Domain Registration',
    description: "Register a real domain through Shopnoltd's registrar service.",
    url: '/domain-registration',
    category: 'Platform',
  },
  {
    icon: '📋',
    name: 'ShopnoltdToolbox',
    description: 'ShopnoltdToolbox-powered data collection.',
    url: 'https://kobotoolbox.shopnoltd.dpdns.org',
    category: 'Productivity',
  },
  {
    icon: '💬',
    name: 'Chat',
    description: 'Customer conversations and team messaging.',
    url: 'https://chat.shopnoltd.dpdns.org',
    category: 'Communication',
  },
  {
    icon: '🔴',
    name: 'Live',
    description: 'Self-hosted live streaming.',
    url: 'https://live.shopnoltd.dpdns.org',
    category: 'Communication',
  },
  {
    icon: '☁️',

    name: 'Drive',
    description: 'Cloud file storage and synchronization.',
    url: 'https://storage.shopnoltd.dpdns.org',
    category: 'Productivity',
  },
  {
    icon: '✉️',
    name: 'Mail',
    description: 'Shopnoltd email services.',
    url: 'https://mail.shopnoltd.dpdns.org',
    category: 'Communication',
  },
  {
    icon: '💳',
    name: 'Billing',
    description: 'Plans, subscriptions, payments and wallet balances in one place.',
    url: 'https://billing.shopnoltd.dpdns.org',
    category: 'Business',
  },
  {
    icon: '💱',
    name: 'Exchange',
    description: 'Manage supported platform balances, transfers and exchange services.',
    url: 'https://exchange.shopnoltd.dpdns.org',
    category: 'Business',
  },
  {
    icon: '🤖',
    name: 'AI',
    description: 'Shopnoltd AI workspace.',
    url: 'https://openai.shopnoltd.dpdns.org',
    category: 'AI',

  },
  {
    icon: '💻',
    name: 'Code',
    description: 'Browser-based development environment.',
    url: 'https://cursor.shopnoltd.dpdns.org',
    category: 'Developer',
  },
  {
    icon: '🔗',
    name: 'API',
    description: 'Connect applications, services, automation and developer tools through Shopnoltd APIs.',
    url: 'https://api.shopnoltd.dpdns.org',
    category: 'Developer',
  },
  {
    icon: '📊',
    name: 'Dashboard',
    description: 'Manage your websites, profile, workspace and social presence in one place.',
    url: '/dashboard',
    category: 'Platform',
  },
  {
    icon: '⚡',
    name: 'Automation',
    description: 'Connect Shopnoltd services and automate workflows, notifications and actions.',
    url: 'https://n8n.shopnoltd.dpdns.org',
    category: 'Automation',
  },
]

const ADMIN_SERVICES = [

  {
    icon: '⚙️',
    name: 'ArgoCD',
    description: 'GitOps deployment management.',
    url: 'https://argocd.shopnoltd.dpdns.org',
  },
]

function ServiceCard({ service }) {
  return (
    
      href={service.url}
      target={service.url.startsWith('/') ? undefined : '_blank'}
      rel={service.url.startsWith('/') ? undefined : 'noopener noreferrer'}
      style={{
        textDecoration: 'none',
        color: 'inherit',
        border: '1px solid #e2e8f0',
        borderRadius: 14,
        padding: 24,
        background: 'white',
        boxShadow: '0 2px 8px rgba(15, 23, 42, 0.06)',
        display: 'block',
      }}
    >
      <div style={{ fontSize: 34 }}>{service.icon}</div>
      <h2 style={{ margin: '12px 0 8px' }}>{service.name}</h2>
      <p style={{ color: '#64748b', minHeight: 48 }}>{service.description}</p>
      <span style={{ color: '#0284c7', fontWeight: 600 }}>Open service →</span>
    </a>
  )
}


export default function Services() {
  return (
    <main style={{
      maxWidth: 1200,
      width: '100%',
      margin: '0 auto',
      padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px)',
      fontFamily: 'system-ui, sans-serif',
      boxSizing: 'border-box',
    }}>
      <h1>Shopnoltd Services</h1>
      <p style={{ color: '#64748b', fontSize: 18 }}>
        All Shopnoltd services in one place — the same services available from your homepage.
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
        gap: 18,
        marginTop: 32,
      }}>
        {SERVICES.map((service) => (
          <ServiceCard key={service.name} service={service} />
        ))}
      </div>

      <section style={{ marginTop: 56 }}>
        <h2>Administration</h2>
        <p style={{ color: '#64748b' }}>
          Infrastructure services for authorized administrators.
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 18,
          marginTop: 18,
        }}>
          {ADMIN_SERVICES.map((service) => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>
      </section>
    </main>
  )
}
