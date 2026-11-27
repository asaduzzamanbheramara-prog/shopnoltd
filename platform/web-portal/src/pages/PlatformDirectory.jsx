import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const styles = {
  page: { maxWidth: 1180, margin: '0 auto', padding: '28px 20px 56px', color: 'var(--text-primary, #172033)' },
  panel: { border: '1px solid var(--border, #dce2ea)', borderRadius: 14, padding: 18, background: 'var(--surface, #fff)' },
  field: { width: '100%', boxSizing: 'border-box', border: '1px solid var(--border, #cbd5e1)', borderRadius: 9, padding: 11, background: 'var(--surface, #fff)', color: 'inherit' },
  grid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(245px, 1fr))', gap: 12, marginTop: 18 },
  muted: { color: 'var(--text-secondary, #64748b)', fontSize: 13, lineHeight: 1.5 },
  pill: { display: 'inline-block', borderRadius: 20, padding: '4px 9px', fontSize: 11, fontWeight: 700, background: '#eef2ff', color: '#3730a3' },
}

const PROVIDER_BY_PLATFORM = {
  facebook: 'facebook', instagram: 'instagram', youtube: 'google', tiktok: 'tiktok',
  linkedin: 'linkedin', x: 'x', telegram: 'telegram', whatsapp: 'whatsapp',
  gmail: 'google', outlook: 'microsoft', '3cx': '3cx',
}

function RuntimeReadiness({ item, providerMap, capabilities }) {
  const providerKey = PROVIDER_BY_PLATFORM[item.id]
  if (!providerKey) return null
  const provider = providerMap[providerKey]
  const actions = capabilities.filter(capability => capability.platform === item.id)
  return <div style={{ borderTop: '1px solid var(--border, #e2e8f0)', marginTop: 12, paddingTop: 10 }}>
    {provider
      ? <p style={styles.muted}>Provider setup: <strong>{provider.setup_status}</strong>. {provider.configured ? 'Credentials are present; account authorization and action verification are still required.' : 'Provider credentials are not configured.'}</p>
      : <p style={styles.muted}>Provider runtime status could not be loaded.</p>}
    {actions.length > 0 && <p style={styles.muted}>Declared actions: {actions.map(action => `${action.action} (${action.availability})`).join(' · ')}</p>}
  </div>
}

export default function PlatformDirectory() {
  const [catalog, setCatalog] = useState({ integrations: [], categories: [], total: 0, catalog_total: 0 })
  const [providers, setProviders] = useState([])
  const [capabilities, setCapabilities] = useState([])
  const [category, setCategory] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setLoading(true)
    Promise.allSettled([
      platformApi.integrationCatalog(category, query),
      platformApi.omnichannelProviders(),
      platformApi.omnichannelCapabilities(),
    ]).then(([catalogResult, providerResult, capabilityResult]) => {
      if (!active) return
      if (catalogResult.status === 'rejected') throw catalogResult.reason
      setCatalog(catalogResult.value)
      setProviders(providerResult.status === 'fulfilled' && Array.isArray(providerResult.value) ? providerResult.value : [])
      setCapabilities(capabilityResult.status === 'fulfilled' && Array.isArray(capabilityResult.value) ? capabilityResult.value : [])
      setError('')
    }).catch(err => { if (active) setError(err.message || 'Could not load the platform directory.') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [category, query])

  const providerMap = useMemo(() => Object.fromEntries(providers.map(item => [item.provider, item])), [providers])
  const existing = useMemo(() => catalog.integrations.filter(item => item.status === 'existing_connector_flow').length, [catalog])

  return <main style={styles.page}>
    <header style={{ marginBottom: 20 }}>
      <p style={{ ...styles.muted, fontWeight: 700, letterSpacing: '.08em', textTransform: 'uppercase' }}>Shopnoltd · Integrations</p>
      <h1 style={{ fontSize: 'clamp(28px, 4vw, 40px)', margin: '8px 0' }}>Platform directory</h1>
      <p style={{ ...styles.muted, maxWidth: 760 }}>Discover commerce, affiliate, advertising, social, finance, CRM, productivity, developer, cloud, logistics and learning platforms. A directory entry is not a claim that the provider is connected or ready to run tasks.</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 14 }}>
        <span style={styles.pill}>{catalog.catalog_total || 0} listed platforms</span>
        <span style={styles.pill}>{existing} with existing Shopnoltd connection flow</span>
        <Link to="/connections" style={{ alignSelf: 'center', fontSize: 13, fontWeight: 700 }}>Manage social connections →</Link>
      </div>
    </header>

    <section style={{ ...styles.panel, display: 'grid', gridTemplateColumns: 'minmax(180px, 1fr) minmax(220px, 2fr)', gap: 12 }}>
      <label style={{ fontSize: 13, fontWeight: 700 }}>Category
        <select value={category} onChange={event => setCategory(event.target.value)} style={{ ...styles.field, marginTop: 6 }}>
          <option value="">All categories</option>
          {catalog.categories.map(item => <option key={item} value={item}>{item}</option>)}
        </select>
      </label>
      <label style={{ fontSize: 13, fontWeight: 700 }}>Search platforms
        <input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search Shopify, Affmine, Stripe, GitHub…" style={{ ...styles.field, marginTop: 6 }} />
      </label>
    </section>

    {error && <p role="alert" style={{ color: '#b91c1c', marginTop: 16 }}>{error}</p>}
    <p style={styles.muted} aria-live="polite">{loading ? 'Loading directory…' : `${catalog.total} results`}</p>
    <section style={styles.grid}>
      {catalog.integrations.map(item => <article key={item.id} style={styles.panel}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
          <h2 style={{ fontSize: 17, margin: 0 }}>{item.name}</h2>
          <span style={{ ...styles.pill, background: item.status === 'existing_connector_flow' ? '#dcfce7' : '#f1f5f9', color: item.status === 'existing_connector_flow' ? '#166534' : '#475569' }}>
            {item.status === 'existing_connector_flow' ? 'Existing flow' : 'Directory only'}
          </span>
        </div>
        <p style={{ ...styles.muted, margin: '8px 0' }}>{item.category} · {item.connection_type.replaceAll('_', ' ')}</p>
        <p style={{ ...styles.muted, minHeight: 58 }}>{item.note}</p>
        <RuntimeReadiness item={item} providerMap={providerMap} capabilities={capabilities} />
        {item.status === 'existing_connector_flow'
          ? <Link to="/connections" style={{ fontWeight: 700, fontSize: 13 }}>Open connection manager →</Link>
          : <span style={{ ...styles.muted, fontWeight: 700 }}>Not yet available for automated execution</span>}
      </article>)}
    </section>
    {!loading && !error && catalog.total === 0 && <p style={styles.panel}>No platforms match this search.</p>}
    <p style={{ ...styles.muted, marginTop: 22 }}>Before enabling a provider, Shopnoltd must verify its official API, regional eligibility, account type, required scopes, provider approval, production credentials, terms, quotas and end-to-end tests. Paid or external actions remain disabled until those checks pass.</p>
  </main>
}
