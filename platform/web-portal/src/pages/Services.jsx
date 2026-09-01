import { SERVICES, CONNECTED_PLATFORMS, ADMIN_SERVICES } from '../data/serviceCatalog'
import { isPlatformAdmin } from '../lib/jwt'

function ServiceCard({ service }) {
  const isInternal = service.url.startsWith('/')

  return (
    <a
      href={service.url}
      target={isInternal ? undefined : '_blank'}
      rel={isInternal ? undefined : 'noopener noreferrer'}
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

      <h2 style={{ margin: '12px 0 8px' }}>
        {service.name}
      </h2>

      <p
        style={{
          color: '#64748b',
          minHeight: 48,
          lineHeight: 1.5,
        }}
      >
        {service.description}
      </p>

      <span
        style={{
          color: '#0284c7',
          fontWeight: 600,
        }}
      >
        Open service →
      </span>
    </a>
  )
}

export default function Services() {
  const isAdmin = !!localStorage.getItem('shopno_token') && isPlatformAdmin()

  return (
    <main
      style={{
        maxWidth: 1200,
        width: '100%',
        margin: '0 auto',
        padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px)',
        fontFamily: 'system-ui, sans-serif',
        boxSizing: 'border-box',
      }}
    >
      <h1>Shopnoltd Services</h1>

      <p
        style={{
          color: '#64748b',
          fontSize: 18,
        }}
      >
        All Shopnoltd services in one place — the same services available
        from your homepage.
      </p>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns:
            'repeat(auto-fit, minmax(240px, 1fr))',
          gap: 18,
          marginTop: 32,
        }}
      >
        {SERVICES.map((service) => (
          <ServiceCard
            key={service.name}
            service={service}
          />
        ))}
      </div>

      <section style={{ marginTop: 56 }}>
        <h2>Connected Platforms</h2>

        <p style={{ color: '#64748b', fontSize: 18 }}>
          One place to access your Shopnoltd services, websites, profiles and
          supported connected platforms.
        </p>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns:
              'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 18,
            marginTop: 18,
          }}
        >
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

          <div
            style={{
              display: 'grid',
              gridTemplateColumns:
                'repeat(auto-fit, minmax(240px, 1fr))',
              gap: 18,
              marginTop: 18,
            }}
          >
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
