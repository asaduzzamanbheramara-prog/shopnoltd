import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { SERVICES, BUSINESS_SERVICES, CONNECTED_PLATFORMS, ADMIN_SERVICES } from '../data/serviceCatalog'
import DomainSearch from '../components/DomainSearch'
import { isPlatformAdmin } from '../lib/jwt'

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || 'https://api.shopnoltd.dpdns.org'

function Card({ service, admin = false }) {
  const internal = service.url.startsWith('/')
  const integration = service.category === 'Social & Messaging'
  const businessApp = service.category === 'Business Apps'
  const badge = admin ? 'ADMIN' : businessApp ? 'BUSINESS APP' : internal ? 'SHOPNOLTD' : integration ? 'INTEGRATION' : 'EXTERNAL SERVICE'
  const action = admin ? 'Open administration →' : businessApp ? 'Create application →' : integration ? 'Configure integration →' : internal ? 'Open workspace →' : 'Open service →'
  const cardStyle = { display: 'flex', flexDirection: 'column', textDecoration: 'none', color: 'inherit', padding: 20, background: 'white', borderRadius: 16, border: '1px solid #e2e8f0', boxShadow: '0 3px 12px rgba(15,23,42,.06)', minHeight: 175 }
  const content = <><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 10 }}><span style={{ fontSize: 32 }}>{service.icon}</span><span style={{ fontSize: 11, fontWeight: 700, color: businessApp ? '#b45309' : integration ? '#7c3aed' : internal ? '#047857' : '#0369a1' }}>{badge}</span></div><h3 style={{ margin: '12px 0 7px' }}>{service.name}</h3><p style={{ margin: 0, color: '#64748b', lineHeight: 1.5, flex: 1 }}>{service.description}</p><span style={{ marginTop: 14, color: '#0284c7', fontWeight: 700 }}>{action}</span></>
  if (internal) {
    return <Link to={service.url} style={cardStyle}>{content}</Link>
  }
  return <a href={service.url} target="_blank" rel="noopener noreferrer" style={cardStyle}>{content}</a>
}

function PreviewSection({ title, description, items, limit = 6, admin = false, href = '/services' }) {
  return <section style={{ marginTop: 48 }}><div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'end', gap: 12, flexWrap: 'wrap' }}><div><h2 style={{ marginBottom: 6 }}>{title}</h2><p style={{ color: '#64748b', marginTop: 0 }}>{description}</p></div>{!admin && <Link to={href} style={{ color: '#0369a1', fontWeight: 700, textDecoration: 'none' }}>View all →</Link>}</div><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 16 }}>{items.slice(0, limit).map(item => <Card key={item.name} service={item} admin={admin} />)}</div></section>
}

function PaymentAccounts() {
  const [accounts, setAccounts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  useEffect(() => {
    let cancelled = false
    fetch(`${API_BASE}/api/v1/payment-accounts/public`, { headers: { Accept: 'application/json' } })
      .then(async (response) => {
        if (!response.ok) throw new Error(`payment account API returned HTTP ${response.status}`)
        return response.json()
      })
      .then((data) => { if (!cancelled) setAccounts(Array.isArray(data) ? data : []) })
      .catch((err) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  async function copy(value, id) {
    if (!value || !navigator.clipboard) return
    await navigator.clipboard.writeText(value)
    setCopied(id)
    window.setTimeout(() => setCopied(''), 1600)
  }

  return <section style={{ marginTop: 52 }}>
    <div style={{ marginBottom: 18 }}><h2 style={{ marginBottom: 6 }}>Shopno Database Firm — Admin Payment Accounts</h2><p style={{ color: '#64748b', margin: 0, lineHeight: 1.6 }}>Use the configured payment method shown below. Public pages display only safe, masked account information; sensitive account values remain restricted to authorized administrators.</p></div>
    {loading && <div style={{ padding: 18, background: '#f8fafc', borderRadius: 14, color: '#64748b' }}>Loading available payment accounts…</div>}
    {!loading && error && <div style={{ padding: 18, background: '#fff7ed', border: '1px solid #fed7aa', borderRadius: 14, color: '#9a3412' }}>Payment accounts are temporarily unavailable.</div>}
    {!loading && !error && !accounts.length && <div style={{ padding: 18, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 14, color: '#64748b' }}>No payment accounts are currently active.</div>}
    {!loading && !error && accounts.length > 0 && <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(260px,1fr))', gap: 16 }}>
      {accounts.map((account) => <article key={account.id} style={{ background: 'white', border: '1px solid #e2e8f0', borderRadius: 16, padding: 20, boxShadow: '0 3px 12px rgba(15,23,42,.06)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start' }}><div><div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: .7, color: '#64748b', fontWeight: 800 }}>{account.provider}</div><h3 style={{ margin: '6px 0' }}>{account.account_label}</h3></div><span style={{ padding: '4px 8px', borderRadius: 999, background: '#ecfdf5', color: '#047857', fontSize: 11, fontWeight: 800 }}>{account.currency}</span></div>
        {account.display_name && <div style={{ marginTop: 10, fontWeight: 600 }}>{account.display_name}</div>}
        {account.masked_account && <div style={{ marginTop: 8, fontFamily: 'ui-monospace,monospace', letterSpacing: .4 }}>{account.masked_account}</div>}
        {account.public_identifier && <div style={{ marginTop: 6, color: '#475569' }}>{account.public_identifier}</div>}
        {account.instructions && <p style={{ margin: '12px 0', color: '#64748b', lineHeight: 1.5 }}>{account.instructions}</p>}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 14 }}>
          {account.public_identifier && <button type="button" onClick={() => copy(account.public_identifier, account.id)} style={{ border: '1px solid #cbd5e1', background: 'white', borderRadius: 8, padding: '8px 11px', cursor: 'pointer' }}>{copied === account.id ? 'Copied' : 'Copy identifier'}</button>}
          {account.payment_url && <a href={account.payment_url} target="_blank" rel="noopener noreferrer" style={{ border: '1px solid #0284c7', background: '#0284c7', color: 'white', borderRadius: 8, padding: '8px 11px', textDecoration: 'none', fontWeight: 700 }}>Pay</a>}
        </div>
        {account.qr_url && <div style={{ marginTop: 16 }}><img src={account.qr_url} alt={`${account.account_label} payment QR`} loading="lazy" style={{ width: 128, height: 128, objectFit: 'contain', border: '1px solid #e2e8f0', borderRadius: 10 }} /></div>}
      </article>)}
    </div>}
  </section>
}

export default function Home() {
  const isAdmin = !!localStorage.getItem('shopno_token') && isPlatformAdmin()
  return <main style={{ maxWidth: 1180, margin: '0 auto', padding: 'clamp(24px,6vw,52px) clamp(14px,4vw,24px) 80px', boxSizing: 'border-box', fontFamily: 'system-ui,sans-serif' }}>
    <DomainSearch />
    <section style={{ margin: '24px 0 44px', padding: 'clamp(28px,6vw,56px)', borderRadius: 24, background: 'linear-gradient(135deg,#0ea5e9,#0369a1)', color: 'white' }}><div style={{ maxWidth: 800 }}><div style={{ fontSize: 44 }}>🌐</div><h1 style={{ fontSize: 'clamp(38px,7vw,68px)', lineHeight: 1.02, margin: '10px 0 18px' }}>All your tools. One platform.</h1><p style={{ fontSize: 'clamp(17px,2.2vw,21px)', lineHeight: 1.7, opacity: .96 }}>Domains, data collection, business applications, communication, calling, social, live media, billing, payments, exchange, AI and developer tools in one Shopnoltd workspace.</p><div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 24 }}><Link to="/services" style={{ padding: '12px 18px', borderRadius: 10, background: 'white', color: '#0369a1', fontWeight: 800, textDecoration: 'none' }}>Explore services</Link><Link to="/domain-registration" style={{ padding: '12px 18px', borderRadius: 10, border: '1px solid rgba(255,255,255,.65)', color: 'white', fontWeight: 800, textDecoration: 'none' }}>Register a domain</Link></div></div></section>
    <PreviewSection title="Core services" description="Start with services managed inside your Shopnoltd workspace, including messaging, calls, notifications and live media." items={SERVICES} />
    <PreviewSection title="Cloud devices" description="Launch browser-accessible Shopnoltd device workspaces." items={SERVICES.filter(service => service.category === 'Cloud Devices')} limit={6} href="/android-cloud" />
    <PreviewSection title="Downloads" description="Install the official Shopnoltd applications on Windows, Linux, macOS or Android." items={SERVICES.filter(service => service.category === 'Downloads')} limit={3} href="/downloads" />
    <PreviewSection title="Business applications" description="Create HR, POS, POS Billing System or ERP applications through the existing website and domain workflow." items={BUSINESS_SERVICES} limit={4} href="/services" />
    <PreviewSection title="Connected platforms" description="Connect supported external platforms through authorized integrations. External availability depends on the provider/API connection." items={CONNECTED_PLATFORMS} limit={6} />
    <PaymentAccounts />
    {isAdmin && <PreviewSection title="Administration" description="Privileged controls for authorized platform administrators." items={ADMIN_SERVICES} limit={6} admin />}
  </main>
}
