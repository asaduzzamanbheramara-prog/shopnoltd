import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const API_BASE = import.meta.env.VITE_API_URL || 'https://api.shopnoltd.dpdns.org/api/v1'

function token() { return localStorage.getItem('shopno_token') }
async function request(path, options = {}) {
  const accessToken = token()
  if (!accessToken) throw new Error('Your session has expired. Please log in again.')
  const response = await fetch(\`\${API_BASE}\${path}\`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: \`Bearer \${accessToken}\`,
      ...(options.headers || {}),
    },
  })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || text || \`HTTP \${response.status}\`)
  return data
}

const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18 }

export default function DomainManagement() {
  const [domains, setDomains] = useState([])
  const [freeDomains, setFreeDomains] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)
  const activeDomains = useMemo(
    () => domains.filter(d => String(d.status).toLowerCase() === 'active'),
    [domains],
  )

  async function load() {
    if (!token()) {
      setLoading(false)
      setError('Please log in to manage your domains.')
      return
    }
    setLoading(true)
    setError('')
    try {
      const [real, free] = await Promise.allSettled([
        request('/domains'),
        request('/free-domains/me'),
      ])
      if (real.status === 'fulfilled') setDomains(Array.isArray(real.value) ? real.value : [])
      else setError(\`Registered domains could not be loaded: \${real.reason?.message || 'domain service unavailable'}\`)
      if (free.status === 'fulfilled') setFreeDomains(Array.isArray(free.value) ? free.value : [])
      else setError(prev => prev || \`Free Shopnoltd domain could not be loaded: \${free.reason?.message || 'free-domain service unavailable'}\`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function renew(name) {
    const years = Number(window.prompt(\`Renew \${name} for how many years?\`, '1'))
    if (!Number.isInteger(years) || years < 1 || years > 10) return
    setBusy(true); setMessage(''); setError('')
    try {
      await request(\`/domains/\${encodeURIComponent(name)}/renew?years=\${years}\`, { method: 'POST' })
      setMessage(\`\${name} renewal completed.\`)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  if (!token()) {
    return <main style={{ maxWidth: 900, margin: '0 auto', padding: '48px 16px 80px' }}>
      <section style={card}>
        <h1>Domain Management</h1>
        <p>Please log in to view and manage domains owned by your account.</p>
        <Link to="/login?next=%2Fdomain-management">Log in →</Link>
      </section>
    </main>
  }

  return <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui,sans-serif' }}>
    <header style={{ marginBottom: 18 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        <div>
          <h1 style={{ marginBottom: 6 }}>Domain Management</h1>
          <p style={{ color: '#64748b', marginTop: 0 }}>
            Every unique Shopnoltd user receives one free <strong>*.shopnoltd.dpdns.org</strong> address. Paid domains remain available separately.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <Link to="/domain-registration">Register paid domain</Link>
          <button onClick={load} disabled={busy || loading}>{loading ? 'Loading…' : 'Refresh'}</button>
        </div>
      </div>
    </header>

    {message && <div role="status" style={{ ...card, marginBottom: 16, background: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' }}>{message}</div>}
    {error && <div role="alert" style={{ ...card, marginBottom: 16, background: '#fff7ed', borderColor: '#fed7aa', color: '#9a3412' }}>{error}</div>}

    <section style={{ ...card, marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>Your free Shopnoltd domain</h2>
      {loading ? <p style={{ color: '#64748b' }}>Provisioning/checking your free domain…</p> :
        freeDomains.length === 0 ? <p style={{ color: '#64748b' }}>No free domain is currently available. Refresh to retry provisioning.</p> :
        <div style={{ padding: 16, borderRadius: 12, background: '#f8fafc', border: '1px solid #e2e8f0' }}>
          <div style={{ fontSize: 20, fontWeight: 800 }}>{freeDomains[0].subdomain}</div>
          <div style={{ marginTop: 6, color: '#64748b' }}>
            {freeDomains[0].record_type} → {freeDomains[0].target} · {freeDomains[0].active ? 'active' : 'inactive'}
          </div>
          <p style={{ marginBottom: 0, color: '#64748b', lineHeight: 1.6 }}>
            This is your single free Shopnoltd subdomain entitlement. You cannot register a second free Shopnoltd subdomain under the same account. You may register any available paid domain separately.
          </p>
        </div>}
    </section>

    <section style={{ ...card, marginBottom: 16 }}>
      <h2 style={{ marginTop: 0 }}>Paid domains</h2>
      <div style={{ color: '#64748b', fontSize: 13 }}>{activeDomains.length} active · {domains.length} total in this account</div>
      {loading ? <p style={{ color: '#64748b' }}>Loading paid domains…</p> :
        domains.length === 0 ? <p style={{ color: '#64748b' }}>No paid domains in this account.</p> :
        domains.map(d => <div key={d.id || d.name} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12, alignItems: 'center', padding: '12px 0', borderTop: '1px solid #e2e8f0' }}>
          <div><strong>{d.name}</strong><div style={{ color: '#64748b', fontSize: 13 }}>{String(d.status || 'unknown').replace(/_/g, ' ')} · expires {d.expires_at ? new Date(d.expires_at).toLocaleDateString() : '—'}</div></div>
          <span>{d.currency || '—'} {d.price ?? '—'}</span>
          <button onClick={() => renew(d.name)} disabled={busy || String(d.status).toLowerCase() !== 'active'}>Renew</button>
        </div>)}
    </section>

    <section style={card}>
      <h2 style={{ marginTop: 0 }}>Referral</h2>
      <p style={{ color: '#64748b', lineHeight: 1.7, marginBottom: 8 }}>
        Your referral code and rewards are managed separately from domain ownership.
      </p>
      <Link to="/referrals">Open Referral Center →</Link>
    </section>
  </main>
}
