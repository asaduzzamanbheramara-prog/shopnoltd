import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

const DOMAIN_API = import.meta.env.VITE_DOMAIN_SERVICE_URL || 'https://domain.shopnoltd.dpdns.org/api/v1'
const FREE_DOMAIN_API = import.meta.env.VITE_FREEDOMAIN_SERVICE_URL || 'https://freedomain.shopnoltd.dpdns.org/api/v1/domains'

function token() {
  return localStorage.getItem('shopno_token')
}

async function request(base, path, options = {}) {
  const accessToken = token()
  if (!accessToken) throw new Error('Your session has expired. Please log in again.')

  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${accessToken}`,
      ...(options.headers || {}),
    },
  })

  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `HTTP ${response.status}`)
  return data
}

const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18 }
const input = { width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }
const statusText = (value) => String(value || 'unknown').replace(/_/g, ' ')

export default function DomainManagement() {
  const [domains, setDomains] = useState([])
  const [freeDomains, setFreeDomains] = useState([])
  const [subdomain, setSubdomain] = useState('')
  const [target, setTarget] = useState('')
  const [recordType, setRecordType] = useState('CNAME')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const activeDomains = useMemo(() => domains.filter((domain) => String(domain.status).toLowerCase() === 'active'), [domains])

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
        request(DOMAIN_API, '/domains'),
        request(FREE_DOMAIN_API, '/me'),
      ])
      if (real.status === 'fulfilled') setDomains(Array.isArray(real.value) ? real.value : [])
      else setError(`Registered domains could not be loaded: ${real.reason?.message || 'domain service unavailable'}`)
      if (free.status === 'fulfilled') setFreeDomains(Array.isArray(free.value) ? free.value : [])
      else setError((previous) => previous || `Free subdomains could not be loaded: ${free.reason?.message || 'free-domain service unavailable'}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function renew(name) {
    const years = Number(window.prompt(`Renew ${name} for how many years?`, '1'))
    if (!Number.isInteger(years) || years < 1 || years > 10) return
    setBusy(true)
    setMessage('')
    setError('')
    try {
      await request(DOMAIN_API, `/domains/${encodeURIComponent(name)}/renew?years=${years}`, { method: 'POST' })
      setMessage(`${name} renewal completed.`)
      await load()
    } catch (err) {
      setError(err.message)
    } finally { setBusy(false) }
  }

  async function createFree(event) {
    event.preventDefault()
    const label = subdomain.trim().toLowerCase()
    const destination = target.trim()
    if (!/^[a-z0-9-]+$/.test(label)) {
      setError('Use only lowercase letters, numbers, and hyphens for the subdomain label.')
      return
    }
    if (!destination) {
      setError('Enter a target hostname or address.')
      return
    }
    setBusy(true)
    setMessage('')
    setError('')
    try {
      const result = await request(FREE_DOMAIN_API, '', {
        method: 'POST',
        body: JSON.stringify({ subdomain: label, target: destination, record_type: recordType }),
      })
      setMessage(`${result?.subdomain || `${label}.shopnoltd.dpdns.org`} is active.`)
      setSubdomain('')
      setTarget('')
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function removeFree(id) {
    if (!window.confirm('Deactivate this free subdomain? This removes the tenant DNS record.')) return
    setBusy(true)
    setMessage('')
    setError('')
    try {
      await request(FREE_DOMAIN_API, `/${encodeURIComponent(id)}`, { method: 'DELETE' })
      setMessage('Free subdomain deactivated.')
      await load()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  if (!token()) {
    return <main style={{ maxWidth: 900, margin: '0 auto', padding: '48px 16px 80px', fontFamily: 'system-ui, sans-serif' }}><section style={card}><h1>Domain Management</h1><p>Please log in to view and manage domains owned by your account.</p><Link to="/login?next=%2Fdomain-management">Log in →</Link></section></main>
  }

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui, sans-serif' }}>
      <header style={{ marginBottom: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', flexWrap: 'wrap' }}>
          <div><h1 style={{ marginBottom: 6 }}>Domain Management</h1><p style={{ color: '#64748b', marginTop: 0 }}>Manage paid domains and your free *.shopnoltd.dpdns.org tenant addresses from one authenticated page.</p></div>
          <div style={{ display: 'flex', gap: 8 }}><Link to="/domain-registration">Register domain</Link><button onClick={load} disabled={busy || loading}>{loading ? 'Loading…' : 'Refresh'}</button></div>
        </div>
      </header>

      {message && <div role="status" style={{ ...card, marginBottom: 16, background: '#f0fdf4', borderColor: '#bbf7d0', color: '#166534' }}>{message}</div>}
      {error && <div role="alert" style={{ ...card, marginBottom: 16, background: '#fff7ed', borderColor: '#fed7aa', color: '#9a3412' }}>{error}</div>}

      <section style={{ ...card, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div><h2 style={{ marginTop: 0, marginBottom: 4 }}>Registered domains</h2><div style={{ color: '#64748b', fontSize: 13 }}>{activeDomains.length} active · {domains.length} total in this account</div></div>
        </div>
        {loading ? <p style={{ color: '#64748b' }}>Loading domains…</p> : domains.length === 0 ? <p style={{ color: '#64748b' }}>No paid domains in this account.</p> : domains.map(domain => (
          <div key={domain.id || domain.name} style={{ display: 'grid', gridTemplateColumns: 'minmax(200px,1fr) minmax(150px,auto) auto', gap: 12, alignItems: 'center', padding: '12px 0', borderTop: '1px solid #e2e8f0' }}>
            <div><strong>{domain.name}</strong><div style={{ color: '#64748b', fontSize: 13 }}>{statusText(domain.status)} · expires {domain.expires_at ? new Date(domain.expires_at).toLocaleDateString() : '—'}</div></div>
            <span>{domain.currency || '—'} {domain.price ?? '—'}</span>
            <button onClick={() => renew(domain.name)} disabled={busy || String(domain.status).toLowerCase() !== 'active'}>Renew</button>
          </div>
        ))}
      </section>

      <section style={{ ...card, marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>Free Shopnoltd subdomain</h2>
        <p style={{ color: '#64748b' }}>Provision an address such as <strong>a.shopnoltd.dpdns.org</strong>. This creates a tenant DNS record; it is not a separate public-domain purchase.</p>
        <form onSubmit={createFree} style={{ display: 'grid', gridTemplateColumns: 'minmax(160px,1fr) minmax(180px,1.4fr) auto auto', gap: 10 }}>
          <input value={subdomain} onChange={e => setSubdomain(e.target.value)} placeholder="a" pattern="[a-z0-9-]+" aria-label="Subdomain label" required style={input} />
          <input value={target} onChange={e => setTarget(e.target.value)} placeholder="Target hostname or address" aria-label="DNS target" required style={input} />
          <select value={recordType} onChange={e => setRecordType(e.target.value)} aria-label="DNS record type" style={input}><option>CNAME</option><option>A</option><option>AAAA</option></select>
          <button type="submit" disabled={busy}>Provision</button>
        </form>
        <div style={{ marginTop: 16 }}>
          {loading ? <p style={{ color: '#64748b' }}>Loading free subdomains…</p> : freeDomains.length === 0 ? <p style={{ color: '#64748b' }}>No free Shopnoltd subdomains in this account.</p> : freeDomains.map(domain => <div key={domain.id || domain.subdomain} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', padding: '10px 0', borderTop: '1px solid #e2e8f0' }}><div><strong>{domain.subdomain}</strong><div style={{ color: '#64748b', fontSize: 13 }}>{domain.record_type} → {domain.target} · {domain.active ? 'active' : 'inactive'}</div></div><button onClick={() => removeFree(domain.id)} disabled={busy || domain.id == null}>Deactivate</button></div>)}
        </div>
      </section>

      <section style={card}>
        <h2 style={{ marginTop: 0 }}>Safe domain lifecycle</h2>
        <ul style={{ color: '#475569', lineHeight: 1.8 }}>
          <li>Availability and pricing are checked by the registrar before payment.</li>
          <li>Registration and renewal are authenticated and charged through the domain service's billing path.</li>
          <li>Paid-domain records are scoped to the logged-in account; free subdomains are tenant-scoped.</li>
          <li>Registrar, billing, and DNS failures are surfaced as errors; the UI never reports success before the service confirms it.</li>
          <li>DNS record editing beyond free-subdomain provisioning is not fabricated here; it requires a corresponding authenticated domain-service API.</li>
        </ul>
      </section>
    </main>
  )
}
