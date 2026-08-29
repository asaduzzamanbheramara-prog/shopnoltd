import { SERVICES, ADMIN_SERVICES } from '../data/serviceCatalog'
import DomainSearch from '../components/DomainSearch'

const CONNECTED_PLATFORMS = [
  {
    icon: '🌐',
    name: 'Web & Websites',
    description: 'Browse, organize and access websites, web apps and connected online services.',
    url: '/dashboard',
  },
  {
    icon: '👤',
    name: 'Profiles',
    description: 'Manage your personal, creator, developer and business profiles from one workspace.',
    url: '/dashboard',
  },
  {
    icon: '📧',
    name: 'Mail',
    description: 'Access Shopnoltd Mail and manage connected email workflows and notifications.',
    url: 'https://mail.shopnoltd.dpdns.org',
  },
  {
    icon: '💬',
    name: 'Messaging',
    description: 'Access conversations, groups, communities and supported messaging connections.',
    url: 'https://chat.shopnoltd.dpdns.org',
  },
  {
    icon: '📞',
    name: 'Calls & Meetings',
    description: 'Access voice, video calls and online meetings through your workspace.',
    url: 'https://meet.shopnoltd.dpdns.org',
  },
  {
    icon: '👥',
    name: 'Social',
    description: 'Organize social profiles, publishing workflows and supported social connections.',
    url: '/dashboard',
  },
  {
    icon: '📺',
    name: 'Video',
    description: 'Manage video channels, publishing, streaming and creator workflows.',
    url: 'https://live.shopnoltd.dpdns.org',
  },
  {
    icon: '⚡',
    name: 'Automation Hub',
    description: 'Automate workflows, notifications and actions between supported services.',
    url: 'https://n8n.shopnoltd.dpdns.org',
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
      padding: 'clamp(28px, 6vw, 52px) clamp(14px, 4vw, 24px) 80px',
      boxSizing: 'border-box',
      width: '100%',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <DomainSearch />
      <section
        style={{
          margin: "24px 0",
          padding: "24px",
          borderRadius: "16px",
          background: "linear-gradient(135deg,#0ea5e9,#0369a1)",
          color: "white"
        }}
      >
        <div style={{fontSize: 36}}>🌐</div>
        <h2>Domain Registration</h2>
        <p>Register a real domain through Shopnoltd's registrar service.</p>
        <a
          href="/domain-registration"
          style={{
            display: "inline-block",
            marginTop: "10px",
            padding: "12px 18px",
            borderRadius: "9px",
            background: "white",
            color: "#0369a1",
            fontWeight: 700,
            textDecoration: "none"
          }}
        >
          Register a domain →
        </a>
      </section>


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
        <h2>Connected Platforms</h2>

        <p style={{ color: '#64748b', maxWidth: 900, lineHeight: 1.6 }}>
          One place to access your Shopnoltd services, websites, profiles and
          supported connected platforms. Use official account connections where
          available and organize your communication, calling, video, social and
          automation workflows from your Shopnoltd workspace.
        </p>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 18,
          marginTop: 18,
        }}>
          {CONNECTED_PLATFORMS.map((service) => (
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
