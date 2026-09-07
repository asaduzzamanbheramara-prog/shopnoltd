import { SERVICES, CONNECTED_PLATFORMS, ADMIN_SERVICES } from '../data/serviceCatalog'
import DomainSearch from '../components/DomainSearch'
import { isPlatformAdmin } from '../lib/jwt'

function Card({ service, admin = false }) {
  const internal = service.url.startsWith('/')
  return <a href={service.url} target={internal ? undefined : '_blank'} rel={internal ? undefined : 'noopener noreferrer'} style={{ display: 'flex', flexDirection: 'column', textDecoration: 'none', color: 'inherit', padding: 20, background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', boxShadow: '0 3px 12px rgba(15,23,42,.06)', minHeight: 175 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}><span style={{ fontSize: 32 }}>{service.icon}</span><span style={{ fontSize: 11, fontWeight: 700, color: internal ? '#047857' : '#0369a1' }}>{admin ? 'ADMIN' : internal ? 'SHOPNOLTD' : 'CONNECTED'}</span></div><h3 style={{ margin: '12px 0 7px' }}>{service.name}</h3><p style={{ margin: 0, color: '#64748b', lineHeight: 1.5, flex: 1 }}>{service.description}</p><span style={{ marginTop: 14, color: '#0284c7', fontWeight: 700 }}>{admin ? 'Open administration →' : internal ? 'Open workspace →' : 'Open service →'}</span></a>
}

function PreviewSection({ title, description, items, limit = 6, admin = false, href = '/services' }) {
  return <section style={{ marginTop: 48 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: 12, flexWrap: 'wrap' }}><div><h2 style={{ marginBottom: 6 }}>{title}</h2><p style={{ color: '#64748b', marginTop: 0 }}>{description}</p></div>{!admin && <a href={href} style={{ color: '#0369a1', fontWeight: 700, textDecoration: 'none' }}>View all →</a>}</div><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 16 }}>{items.slice(0, limit).map(item => <Card key={item.name} service={item} admin={admin} />)}</div></section>
}

export default function Home() {
  const isAdmin = !!localStorage.getItem('shopno_token') && isPlatformAdmin()
  return <main style={{ maxWidth: 1180, margin: '0 auto', padding: 'clamp(24px,6vw,52px) clamp(14px,4vw,24px) 80px', boxSizing: 'border-box', fontFamily: 'system-ui,sans-serif' }}>
    <DomainSearch />
    <section style={{ margin: '24px 0 44px', padding: 'clamp(28px,6vw,56px)', borderRadius: 24, background: 'linear-gradient(135deg,#0ea5e9,#0369a1)', color: 'white' }}><div style={{ maxWidth: 800 }}><div style={{ fontSize: 44 }}>🌐</div><h1 style={{ fontSize: 'clamp(38px,7vw,68px)', lineHeight: 1.02, margin: '10px 0 18px' }}>All your tools. One platform.</h1><p style={{ fontSize: 'clamp(17px,2.2vw,21px)', lineHeight: 1.7, opacity: .96 }}>Domains, data collection, communication, billing, payments, exchange, AI and developer tools in one Shopnoltd workspace.</p><div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 24 }}><a href="/services" style={{ padding: '12px 18px', borderRadius: 10, background: 'white', color: '#0369a1', fontWeight: 800, textDecoration: 'none' }}>Explore services</a><a href="/domain-registration" style={{ padding: '12px 18px', borderRadius: 10, border: '1px solid rgba(255,255,255,.65)', color: 'white', fontWeight: 800, textDecoration: 'none' }}>Register a domain</a></div></div></section>
    <PreviewSection title="Core services" description="Start with the services managed inside your Shopnoltd workspace." items={SERVICES} />
    <PreviewSection title="Connected platforms" description="Connect supported external platforms through authorized integrations. External availability depends on the provider/API connection." items={CONNECTED_PLATFORMS} limit={6} />
    {isAdmin && <PreviewSection title="Administration" description="Privileged controls for authorized platform administrators." items={ADMIN_SERVICES} limit={6} admin />}
  </main>
}
