import React, { useEffect, useState } from 'react'
import { isPlatformAdmin } from '../lib/jwt'

const API = '/api/v1/ads'

function token() {
  return localStorage.getItem('shopno_token') || ''
}

async function api(path, options = {}) {
  const headers = { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}) }
  const t = token()
  if (t) headers.Authorization = `Bearer ${t}`
  const response = await fetch(`${API}${path}`, { ...options, headers })
  const text = await response.text()
  let body = {}
  try { body = text ? JSON.parse(text) : {} } catch { body = { detail: text } }
  if (!response.ok) throw new Error(body.detail || `Request failed (${response.status})`)
  return body
}

function Card({ title, children }) {
  return <section style={{ background: 'white', border: '1px solid #dbeafe', borderRadius: 14, padding: 20, boxShadow: '0 4px 18px rgba(15,23,42,.05)' }}>
    <h2 style={{ marginTop: 0, color: '#0f172a' }}>{title}</h2>
    {children}
  </section>
}

function Status({ value }) {
  const text = value || 'not registered'
  return <span style={{ display: 'inline-block', padding: '4px 9px', borderRadius: 999, background: '#eff6ff', color: '#1d4ed8', fontSize: 13 }}>{text}</span>
}

export default function AdNetwork() {
  const [advertiser, setAdvertiser] = useState(null)
  const [publisher, setPublisher] = useState(null)
  const [campaigns, setCampaigns] = useState([])
  const [siteDomain, setSiteDomain] = useState('')
  const [campaign, setCampaign] = useState({ name: '', budget_minor: 1000, currency: 'USD', starts_at: '', ends_at: '' })
  const [adminAdvertisers, setAdminAdvertisers] = useState([])
  const [adminPublishers, setAdminPublishers] = useState([])
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const admin = isPlatformAdmin()

  const refresh = async () => {
    setLoading(true); setError('')
    try {
      const [a, p] = await Promise.allSettled([api('/advertisers/me'), api('/publishers/me')])
      if (a.status === 'fulfilled') setAdvertiser(a.value); else if (a.reason?.message?.includes('not found')) setAdvertiser(null); else throw a.reason
      if (p.status === 'fulfilled') setPublisher(p.value); else if (p.reason?.message?.includes('not found')) setPublisher(null); else throw p.reason
      if (a.status === 'fulfilled') {
        const c = await api('/campaigns')
        setCampaigns(Array.isArray(c) ? c : [])
      } else setCampaigns([])
      if (admin) {
        const [aa, ap] = await Promise.all([api('/admin/advertisers'), api('/admin/publishers')])
        setAdminAdvertisers(aa); setAdminPublishers(ap)
      }
    } catch (e) { setError(e.message || 'Could not load advertising data') }
    finally { setLoading(false) }
  }

  useEffect(() => { refresh() }, [])

  const run = async (fn) => {
    setError(''); setMessage('')
    try { await fn(); setMessage('Shopnoltd advertising account updated successfully.'); await refresh() }
    catch (e) { setError(e.message || 'Request failed') }
  }

  const registerAdvertiser = () => run(async () => {
    const display_name = window.prompt('Advertiser / business display name')
    if (!display_name?.trim()) return
    await api('/advertisers', { method: 'POST', body: JSON.stringify({ display_name: display_name.trim() }) })
  })

  const registerPublisher = () => run(async () => {
    const display_name = window.prompt('Publisher / website owner display name')
    if (!display_name?.trim()) return
    await api('/publishers', { method: 'POST', body: JSON.stringify({ display_name: display_name.trim() }) })
  })

  const createCampaign = () => run(async () => {
    if (!campaign.name || !campaign.starts_at || !campaign.ends_at) throw new Error('Campaign name, start time and end time are required.')
    await api('/campaigns', { method: 'POST', body: JSON.stringify({ ...campaign, budget_minor: Number(campaign.budget_minor) }) })
    setCampaign({ name: '', budget_minor: 1000, currency: 'USD', starts_at: '', ends_at: '' })
  })

  const registerSite = () => run(async () => {
    if (!siteDomain.trim()) throw new Error('Enter a website domain.')
    await api('/publishers/sites', { method: 'POST', body: JSON.stringify({ domain: siteDomain.trim() }) })
    setSiteDomain('')
  })

  const approve = (kind, id) => run(async () => {
    await api(`/admin/${kind}/${id}/approve`, { method: 'POST' })
  })

  return <main style={{ maxWidth: 1180, margin: '0 auto', padding: '36px 20px 70px', background: '#f8fafc', minHeight: '80vh' }}>
    <div style={{ marginBottom: 28 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#0369a1', letterSpacing: '.08em', textTransform: 'uppercase' }}>Shopnoltd Advertising Network</div>
      <h1 style={{ margin: '7px 0 10px', color: '#0f172a' }}>Advertise or publish with Shopnoltd</h1>
      <p style={{ maxWidth: 850, lineHeight: 1.7, color: '#475569' }}>
        The Shopnoltd-owned advertising foundation is live. Accounts, approvals, campaign funding and verified publisher inventory are protected by the platform API.
        <strong> Paid delivery is intentionally fail-closed until all financial, consent/privacy, fraud, signing and event-ledger gates are complete.</strong>
      </p>
    </div>

    {message && <div role="status" style={{ marginBottom: 16, padding: 12, borderRadius: 10, background: '#ecfdf5', color: '#166534' }}>{message}</div>}
    {error && <div role="alert" style={{ marginBottom: 16, padding: 12, borderRadius: 10, background: '#fef2f2', color: '#991b1b' }}>{error}</div>}
    {loading ? <p>Loading advertising accounts…</p> : <div style={{ display: 'grid', gap: 18 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 18 }}>
        <Card title="Advertiser">
          {advertiser ? <><p><strong>{advertiser.legal_name}</strong></p><p>Status: <Status value={advertiser.status} /></p></> : <><p>No advertiser account yet.</p><button onClick={registerAdvertiser}>Create advertiser account</button></>}
        </Card>
        <Card title="Publisher">
          {publisher ? <><p><strong>{publisher.display_name}</strong></p><p>Status: <Status value={publisher.status} /></p><p>Revenue share: {publisher.revenue_share_bps / 100}%</p></> : <><p>No publisher account yet.</p><button onClick={registerPublisher}>Create publisher account</button></>}
        </Card>
      </div>

      {advertiser && <Card title="Campaigns">
        <form onSubmit={(e) => { e.preventDefault(); createCampaign() }} style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', alignItems: 'end' }}>
          <label>Name<input value={campaign.name} onChange={e => setCampaign({ ...campaign, name: e.target.value })} required /></label>
          <label>Budget (minor units)<input type="number" min="1" value={campaign.budget_minor} onChange={e => setCampaign({ ...campaign, budget_minor: e.target.value })} /></label>
          <label>Currency<input maxLength="3" value={campaign.currency} onChange={e => setCampaign({ ...campaign, currency: e.target.value.toUpperCase() })} /></label>
          <label>Starts<input type="datetime-local" value={campaign.starts_at} onChange={e => setCampaign({ ...campaign, starts_at: e.target.value })} required /></label>
          <label>Ends<input type="datetime-local" value={campaign.ends_at} onChange={e => setCampaign({ ...campaign, ends_at: e.target.value })} required /></label>
          <button type="submit">Create campaign</button>
        </form>
        <div style={{ overflowX: 'auto', marginTop: 18 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}><thead><tr><th align="left">Name</th><th>Status</th><th>Budget</th><th>Spent</th></tr></thead><tbody>
            {campaigns.length ? campaigns.map(c => <tr key={c.id}><td>{c.name}</td><td><Status value={c.status} /></td><td>{c.budget_minor} {c.currency}</td><td>{c.spent_minor} {c.currency}</td></tr>) : <tr><td colSpan="4">No campaigns yet.</td></tr>}
          </tbody></table>
        </div>
      </Card>}

      {publisher && <Card title="Publisher inventory">
        <p style={{ color: '#475569' }}>Your publisher account must be approved before a site can be registered. Site ownership verification is required before an ad zone can be created.</p>
        <form onSubmit={(e) => { e.preventDefault(); registerSite() }} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <input placeholder="example.com" value={siteDomain} onChange={e => setSiteDomain(e.target.value)} />
          <button type="submit">Register website</button>
        </form>
      </Card>}

      {admin && <Card title="Admin approvals">
        <h3>Advertisers</h3>
        {adminAdvertisers.map(x => <div key={x.id} style={{ display: 'flex', gap: 10, alignItems: 'center', margin: '8px 0' }}><span>{x.legal_name} — <Status value={x.status} /></span>{x.status !== 'approved' && <button onClick={() => approve('advertisers', x.id)}>Approve</button>}</div>)}
        <h3>Publishers</h3>
        {adminPublishers.map(x => <div key={x.id} style={{ display: 'flex', gap: 10, alignItems: 'center', margin: '8px 0' }}><span>{x.display_name} — <Status value={x.status} /></span>{x.status !== 'approved' && <button onClick={() => approve('publishers', x.id)}>Approve</button>}</div>)}
      </Card>}
    </div>}
  </main>
}
