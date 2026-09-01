import { SERVICES, CONNECTED_PLATFORMS, ADMIN_SERVICES } from '../data/serviceCatalog'
import DomainSearch from '../components/DomainSearch'
import { isPlatformAdmin } from '../lib/jwt'

function ServiceCard({ service }) {
  const isInternal = service.url.startsWith('/')

  return (
    <a
      href={service.url}
      target={isInternal ? undefined : '_blank'}
      rel={isInternal ? undefined : 'noopener noreferrer'}
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
  const isAdmin = !!localStorage.getItem('shopno_token') && isPlatformAdmin()

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

      {isAdmin && (
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
      )}
    </main>
  )
}
