import { useMemo, useState } from 'react'
import { SERVICES, BUSINESS_SERVICES, CONNECTED_PLATFORMS, ADMIN_SERVICES } from '../data/serviceCatalog'
import { isPlatformAdmin } from '../lib/jwt'

const ALL = [...SERVICES, ...BUSINESS_SERVICES, ...CONNECTED_PLATFORMS]

function ServiceCard({ service, admin = false }) {
  const internal = service.url.startsWith('/')
  const integration = service.category === 'Social & Messaging'
  const businessApp = service.category === 'Business Apps'
  const action = admin ? 'Open administration' : businessApp ? 'Create application' : integration ? 'Configure integration' : internal ? 'Open workspace' : 'Open service'
  const badge = internal ? (businessApp ? 'Business app' : 'Shopnoltd') : integration ? 'Integration' : 'External service'
  const badgeStyle = businessApp ? { color: '#b45309', background: '#fffbeb' } : internal ? { color: '#047857', background: '#ecfdf5' } : integration ? { color: '#7c3aed', background: '#f5f3ff' } : { color: '#0369a1', background: '#eff6ff' }
  return (
    <a href={service.url} target={internal ? undefined : '_blank'} rel={internal ? undefined : 'noopener noreferrer'} style={{ textDecoration: 'none', color: 'inherit', border: '1px solid #e2e8f0', borderRadius: 16, padding: 22, background: 'white', boxShadow: '0 3px 12px rgba(15,23,42,.06)', display: 'flex', flexDirection: 'column', minHeight: 190 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}><span style={{ fontSize: 34 }}>{service.icon}</span><span style={{ ...badgeStyle, fontSize: 12, fontWeight: 700, padding: '5px 8px', borderRadius: 999 }}>{badge}</span></div>
      <h2 style={{ margin: '12px 0 8px', fontSize: 20 }}>{service.name}</h2>
      <p style={{ color: '#64748b', lineHeight: 1.5, margin: 0, flex: 1 }}>{service.description}</p>
      <span style={{ color: '#0284c7', fontWeight: 700, marginTop: 16 }}>{action} →</span>
    </a>
  )
}

function Section({ title, description, items, admin = false }) {
  return <section style={{ marginTop: 42 }}><h2 style={{ marginBottom: 6 }}>{title}</h2><p style={{ color: '#64748b', lineHeight: 1.6, marginTop: 0 }}>{description}</p><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 18, marginTop: 18 }}>{items.map(service => <ServiceCard key={service.name} service={service} admin={admin} />)}</div></section>
}

export default function Services() {
  const isAdmin = !!localStorage.getItem('shopno_token') && isPlatformAdmin()
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState('All')
  const categories = useMemo(() => ['All', ...new Set(ALL.map(item => item.category))], [])
  const filtered = useMemo(() => ALL.filter(item => (category === 'All' || item.category === category) && `${item.name} ${item.description} ${item.category}`.toLowerCase().includes(query.toLowerCase())), [category, query])
  const services = filtered.filter(item => SERVICES.some(x => x.name === item.name))
  const businessApps = filtered.filter(item => BUSINESS_SERVICES.some(x => x.name === item.name))
  const connected = filtered.filter(item => CONNECTED_PLATFORMS.some(x => x.name === item.name))
  return <main style={{ maxWidth: 1200, width: '100%', margin: '0 auto', padding: 'clamp(28px,6vw,52px) clamp(14px,4vw,24px) 80px', boxSizing: 'border-box', fontFamily: 'system-ui,sans-serif' }}>
    <section style={{ padding: '28px clamp(20px,5vw,44px)', borderRadius: 20, background: 'linear-gradient(135deg,#0ea5e9,#0369a1)', color: 'white' }}><div style={{ fontSize: 40 }}>🧭</div><h1 style={{ fontSize: 'clamp(32px,5vw,48px)', margin: '8px 0' }}>Shopnoltd Services</h1><p style={{ maxWidth: 760, lineHeight: 1.7, marginBottom: 0, opacity: .95 }}>One service directory for your workspace, business tools, developer tools, communications, business application builders and supported integrations.</p></section>
    <section style={{ display: 'grid', gridTemplateColumns: 'minmax(220px,1fr) minmax(180px,240px)', gap: 12, marginTop: 24 }}><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search services, tools or integrations…" aria-label="Search services" style={{ padding: 13, border: '1px solid #cbd5e1', borderRadius: 10, fontSize: 15 }} /><select value={category} onChange={e => setCategory(e.target.value)} aria-label="Filter by category" style={{ padding: 13, border: '1px solid #cbd5e1', borderRadius: 10, background: 'white', fontSize: 15 }}>{categories.map(item => <option key={item}>{item}</option>)}</select></section>
    <p style={{ color: '#64748b', fontSize: 14, marginTop: 12 }}>{filtered.length} services and connected platforms shown.</p>
    <Section title="Shopnoltd Services" description="Core services available through the Shopnoltd workspace." items={services} />
    <Section title="Business Applications" description="HR, POS, POS Billing System and ERP are first-class website-builder targets. Creating one carries the selected type into the existing domain/site workflow." items={businessApps} />
    <Section title="Connected Platforms" description="External platforms and integration workflows. Availability depends on the authorized provider/API connection." items={connected} />
    {isAdmin && <Section title="Administration" description="Privileged administration surfaces for authorized platform administrators." items={ADMIN_SERVICES} admin />}
    {!filtered.length && <div style={{ padding: 30, marginTop: 24, border: '1px dashed #cbd5e1', borderRadius: 14, textAlign: 'center', color: '#64748b' }}>No matching service. Try another search or category.</div>}
  </main>
}
