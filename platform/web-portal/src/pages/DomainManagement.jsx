import { useEffect, useState } from 'react'

const DOMAIN_API = import.meta.env.VITE_DOMAIN_SERVICE_URL || 'https://domain.shopnoltd.dpdns.org/api/v1'
const FREE_DOMAIN_API = import.meta.env.VITE_FREEDOMAIN_SERVICE_URL || 'https://freedomain.shopnoltd.dpdns.org/api/v1/domains'

function token() {
  return localStorage.getItem('shopno_token')
}

async function request(base, path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      Authorization: `Bearer ${token()}`,
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

export default function DomainManagement() {
  const [domains, setDomains] = useState([])
  const [freeDomains, setFreeDomains] = useState([])
  const [subdomain, setSubdomain] = useState('')
  const [target, setTarget] = useState('')
  const [recordType, setRecordType] = useState('CNAME')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  async function load() {
    setBusy(true)
    setMessage('')
    try {
      const [real, free] = await Promise.all([
        request(DOMAIN_API, '/domains'),
        request(FREE_DOMAIN_API, '/me'),
      ])
      setDomains(Array.isArray(real) ? real : [])
      setFreeDomains(Array.isArray(free) ? free : [])
    } catch (error) {
      setMessage(error.message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { load() }, [])

  async function renew(name) {
    const years = Number(window.prompt(`Renew ${name} for how many years?`, '1'))
    if (!Number.isInteger(years) || years < 1 || years > 10) return
    setBusy(true)
    try {
      await request(DOMAIN_API, `/domains/${encodeURIComponent(name)}/renew?years=${years}`, { method: 'POST' })
      setMessage(`${name} renewed successfully.`)
      await load()
    } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }

  async function createFree(event) {
    event.preventDefault()
    if (!subdomain.trim() || !target.trim()) return
    setBusy(true)
    try {
      const result = await request(FREE_DOMAIN_API, '', {
        method: 'POST',
        body: JSON.stringify({ subdomain: subdomain.trim().toLowerCase(), target: target.trim(), record_type: recordType }),
      })
      setMessage(`${result.subdomain} is active.`)
      setSubdomain('')
      setTarget('')
      await load()
    } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }

  async function removeFree(id) {
    if (!window.confirm('Deactivate this free subdomain?')) return
    setBusy(true)
    try {
      await request(FREE_DOMAIN_API, `/${encodeURIComponent(id)}`, { method: 'DELETE' })
      await load()
    } catch (error) { setMessage(error.message) } finally { setBusy(false) }
  }

  return (
    <main style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 16px 80px', fontFamily: 'system-ui, sans-serif' }}>
      <h1>Domain Management</h1>
      <p style={{ color: '#64748b' }}>Manage paid domains and your free *.shopnoltd.dpdns.org tenant addresses from one authenticated page.</p>
      {message && <div style={{ ...card, marginBottom: 16, background: '#f8fafc' }}>{message}</div>}

      <section style={{ ...card, marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <h2 style={{ marginTop: 0 }}>Registered domains</h2>
          <button onClick={load} disabled={busy}>Refresh</button>
        </div>
        {domains.length === 0 ? <p style={{ color: '#64748b' }}>No paid domains in this account.</p> : domains.map(domain => (
          <div key={domain.id} style={{ display: 'grid', gridTemplateColumns: 'minmax(180px,1fr) auto auto', gap: 12, alignItems: 'center', padding: '12px 0', borderTop: '1px solid #e2e8f0' }}>
            <div><strong>{domain.name}</strong><div style={{ color: '#64748b', fontSize: 13 }}>{domain.status} · expires {domain.expires_at ? new Date(domain.expires_at).toLocaleDateString() : '—'}</div></div>
            <span>{domain.currency} {domain.price}</span>
            <button onClick={() => renew(domain.name)} disabled={busy}>Renew</button>
          </div>
        ))}
      </section>

      <section style={{ ...card, marginBottom: 16 }}>
        <h2 style={{ marginTop: 0 }}>Free Shopnoltd subdomain</h2>
        <p style={{ color: '#64748b' }}>Provision an address such as <strong>a.shopnoltd.dpdns.org</strong>. This is a DNS tenant record, not a separate public-domain purchase.</p>
        <form onSubmit={createFree} style={{ display: 'grid', gridTemplateColumns: 'minmax(160px,1fr) minmax(180px,1.4fr) auto auto', gap: 10 }}>
          <input value={subdomain} onChange={e => setSubdomain(e.target.value)} placeholder="a" pattern="[a-z0-9-]+" required style={input} />
          <input value={target} onChange={e => setTarget(e.target.value)} placeholder="Target hostname or address" required style={input} />
          <select value={recordType} onChange={e => setRecordType(e.target.value)} style={input}><option>CNAME</option><option>A</option><option>AAAA</option></select>
          <button type="submit" disabled={busy}>Provision</button>
        </form>
        <div style={{ marginTop: 16 }}>
          {freeDomains.map(domain => <div key={domain.id} style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', padding: '10px 0', borderTop: '1px solid #e2e8f0' }}><div><strong>{domain.subdomain}</strong><div style={{ color: '#64748b', fontSize: 13 }}>{domain.record_type} → {domain.target} · {domain.active ? 'active' : 'inactive'}</div></div><button onClick={() => removeFree(domain.id)} disabled={busy}>Deactivate</button></div>)}
        </div>
      </section>

      <section style={card}>
        <h2 style={{ marginTop: 0 }}>Safe domain lifecycle</h2>
        <ul style={{ color: '#475569', lineHeight: 1.8 }}>
          <li>Availability and pricing are checked by the registrar before payment.</li>
          <li>Renewal uses the same authenticated wallet billing path.</li>
          <li>Free subdomains are isolated to the logged-in tenant.</li>
          <li>Registrar and DNS failures are surfaced; the UI never reports fake success.</li>
        </ul>
      </section>
    </main>
  )
}
