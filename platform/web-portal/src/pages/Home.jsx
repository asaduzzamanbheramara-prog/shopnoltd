const SERVICES = [
  {
    icon: '📋',
    name: 'Surveys',
    description: 'KoboToolbox-powered data collection.',
    url: 'https://kf.shopnoltd.dpdns.org',
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
    icon: '📹',
    name: 'Meet',
    description: 'Video conferencing with Jitsi.',
    url: 'https://meet.shopnoltd.dpdns.org',
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
    icon: '🏢',
    name: 'ERP',
    description: 'Business management and ERP.',
    url: 'https://erp.shopnoltd.dpdns.org',
    category: 'Business',
  },
  {
    icon: '💳',
    name: 'Billing',
    description: 'Plans, subscriptions and payments.',
    url: 'https://billing.shopnoltd.dpdns.org',
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
]

const ADMIN_SERVICES = [
  {
    icon: '📊',
    name: 'Grafana',
    description: 'Monitoring and observability.',
    url: 'https://grafana.shopnoltd.dpdns.org',
  },
  {
    icon: '📈',
    name: 'Prometheus',
    description: 'Metrics and monitoring.',
    url: 'https://prometheus.shopnoltd.dpdns.org',
  },
  {
    icon: '⚙️',
    name: 'ArgoCD',
    description: 'GitOps deployment management.',
    url: 'https://argocd.shopnoltd.dpdns.org',
  },
  {
    icon: '🛠️',
    name: 'Portainer',
    description: 'Infrastructure management.',
    url: 'https://portainer.shopnoltd.dpdns.org',
  },
]

function ServiceCard({ service }) {
  return (
    <a
      href={service.url}
      target="_blank"
      rel="noopener noreferrer"
      style={{
        display: 'block',
        textDecoration: 'none',
        color: 'inherit',
        padding: 22,
        background: 'white',
        borderRadius: 14,
        border: '1px solid #e2e8f0',
        boxShadow: '0 2px 8px rgba(15,23,42,.06)',
      }}
    >
      <div style={{ fontSize: 34 }}>{service.icon}</div>

      <h3 style={{
        margin: '12px 0 6px',
        color: '#0f172a',
      }}>
        {service.name}
      </h3>

      <p style={{
        margin: 0,
        color: '#64748b',
        lineHeight: 1.5,
      }}>
        {service.description}
      </p>

      <div style={{
        marginTop: 14,
        color: '#0284c7',
        fontWeight: 600,
      }}>
        Open service →
      </div>
    </a>
  )
}

export default function Home() {
  return (
    <main style={{
      maxWidth: 1180,
      margin: '0 auto',
      padding: '52px 24px 80px',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <section style={{
        textAlign: 'center',
        marginBottom: 52,
      }}>
        <h1 style={{
          color: '#0ea5e9',
          fontSize: 'clamp(38px, 6vw, 64px)',
          marginBottom: 18,
        }}>
          All your tools. One platform.
        </h1>

        <p style={{
          maxWidth: 850,
          margin: '0 auto',
          fontSize: 19,
          lineHeight: 1.7,
          color: '#475569',
        }}>
          Shopnoltd brings together surveys, chat, video meetings,
          live streaming, cloud storage, email, business tools,
          AI and developer tools under one account.
        </p>
      </section>

      <section>
        <h2>Shopnoltd Services</h2>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 18,
          marginTop: 18,
        }}>
          {SERVICES.map((service) => (
            <ServiceCard
              key={service.name}
              service={service}
            />
          ))}
        </div>
      </section>

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
            <ServiceCard
              key={service.name}
              service={service}
            />
          ))}
        </div>
      </section>
    </main>
  )
}
