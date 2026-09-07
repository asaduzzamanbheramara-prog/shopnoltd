import { useMemo, useState } from 'react'
import { Database, ShieldCheck, Lock, RefreshCw, FileDown, BarChart3 } from 'lucide-react'

const PAYMENT_API = import.meta.env.VITE_PAYMENT_API_URL || 'https://payment-service.shopnoltd.dpdns.org'

const SERVICES = [
  { service: 'payment-service', database: 'PostgreSQL', mode: 'service API + guarded admin adapter', genericWrites: false, capabilities: ['view', 'search', 'filter', 'analysis', 'CSV/JSON/XLSX export', 'PDF reports', 'audit', 'backup/restore'], protected: 'wallets, transactions, webhooks, audit/security data' },
  { service: 'billing-engine', database: 'PostgreSQL', mode: 'service API + guarded admin adapter', genericWrites: false, capabilities: ['view', 'search', 'analysis', 'reports', 'audit', 'backup/restore'], protected: 'wallet/ledger and billing events' },
  { service: 'exchange-service', database: 'PostgreSQL', mode: 'service API + admin adapter', genericWrites: false, capabilities: ['view', 'search', 'analysis', 'reports', 'audit', 'backup/restore'], protected: 'rate/provider history' },
  { service: 'auth-service / Keycloak', database: 'identity store', mode: 'service-specific administration API', genericWrites: false, capabilities: ['user lifecycle', 'roles', 'search', 'audit', 'reports', 'backup/restore'], protected: 'credentials, tokens, password material, identity internals' },
  { service: 'domain-service', database: 'PostgreSQL', mode: 'service API', genericWrites: 'controlled', capabilities: ['search', 'safe record edits', 'reports', 'audit', 'backup'], protected: 'registration, renewal, billing, registrar workflows' },
  { service: 'freedomain-service', database: 'PostgreSQL', mode: 'service API', genericWrites: 'controlled', capabilities: ['tenant/domain search', 'lifecycle operations', 'reports', 'audit', 'backup'], protected: 'DNS and registrar workflows' },
  { service: 'ai-platform', database: 'PostgreSQL', mode: 'service API + admin adapter', genericWrites: 'controlled', capabilities: ['provider/model CRUD', 'activation', 'analysis', 'reports', 'audit', 'backup'], protected: 'API keys and provider secrets' },
  { service: 'social/blog', database: 'PostgreSQL', mode: 'service API + admin adapter', genericWrites: true, capabilities: ['CRUD', 'draft/publish', 'search', 'import/export', 'reports', 'audit', 'backup'], protected: 'account/security records' },
  { service: 'api-service', database: 'service state', mode: 'service API', genericWrites: false, capabilities: ['resource management', 'search', 'reports', 'audit', 'backup'], protected: 'auth/session/security state' },
  { service: 'audit-service', database: 'append-only store', mode: 'append-only service', genericWrites: false, capabilities: ['search', 'filter', 'analysis', 'export/report', 'retention', 'backup/restore'], protected: 'historical audit events' },
  { service: 'event-service', database: 'event store', mode: 'service API', genericWrites: false, capabilities: ['search', 'filter', 'validated replay', 'analysis', 'reports', 'backup'], protected: 'event/idempotency history' },
  { service: 'analytics-service', database: 'analytics store', mode: 'service API', genericWrites: 'controlled', capabilities: ['datasets', 'queries', 'dashboards', 'analysis', 'reports', 'export', 'backup'], protected: 'source-system records remain source-owned' },
  { service: 'KoboToolbox / KoBoCat / Enketo', database: 'application stores', mode: 'application-native APIs', genericWrites: 'application-defined', capabilities: ['forms/projects', 'submissions', 'search', 'export', 'analysis', 'reports', 'backup'], protected: 'application authentication and internals' },
  { service: 'mail / meeting / storage', database: 'application metadata', mode: 'application/service APIs', genericWrites: 'controlled', capabilities: ['configuration', 'search', 'usage analysis', 'reports', 'backup'], protected: 'passwords, tokens, credentials, ACL-protected content' },
]

const STATUS = {
  true: { label: 'Controlled CRUD', tone: '#3fb950' },
  controlled: { label: 'Controlled', tone: '#e3b341' },
  false: { label: 'Read-only generic', tone: '#7d8a9c' },
  'application-defined': { label: 'Application-defined', tone: '#7d8a9c' },
}

function authHeaders() {
  const token = localStorage.getItem('shopno_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export default function DatabaseControlPlane() {
  const [selected, setSelected] = useState(SERVICES[0].service)
  const [tables, setTables] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const current = useMemo(() => SERVICES.find((item) => item.service === selected) || SERVICES[0], [selected])

  async function inspectPaymentDatabase() {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${PAYMENT_API}/api/v1/admin/tables`, { headers: { Accept: 'application/json', ...authHeaders() } })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = await response.json()
      setTables(Array.isArray(data) ? data : [])
    } catch (err) {
      setError(`Payment database inspection failed: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main style={{ minHeight: 'calc(100vh - 64px)', background: '#0f1419', color: '#e6edf3', padding: 'clamp(16px, 3vw, 32px)' }}>
      <div style={{ maxWidth: 1500, margin: '0 auto' }}>
        <header style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}>
            <Database size={24} color="#d4a054" />
            <h1 style={{ margin: 0, fontSize: 'clamp(24px, 4vw, 36px)' }}>Database Control Plane</h1>
          </div>
          <p style={{ color: '#7d8a9c', maxWidth: 900, lineHeight: 1.6, margin: 0 }}>
            Cross-service inventory and capability boundary. Operations are advertised explicitly; protected financial, identity, audit and security entities remain behind their owning service APIs.
          </p>
        </header>

        <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12, marginBottom: 20 }}>
          <Metric icon={<Database size={18} />} label="Data domains" value={SERVICES.length} />
          <Metric icon={<ShieldCheck size={18} />} label="Controlled boundaries" value={SERVICES.filter((x) => x.genericWrites !== true).length} />
          <Metric icon={<Lock size={18} />} label="Generic financial writes" value="0" />
          <Metric icon={<BarChart3 size={18} />} label="Analysis/reporting" value="Required" />
        </section>

        {error && <div style={{ padding: 12, marginBottom: 16, border: '1px solid #f85149', borderRadius: 8, color: '#ffb4af' }}>{error}</div>}

        <section style={{ display: 'grid', gridTemplateColumns: 'minmax(240px,320px) minmax(0,1fr)', gap: 16, alignItems: 'start' }}>
          <aside style={{ background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 10 }}>
            <div style={{ color: '#7d8a9c', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.8, padding: '8px 10px' }}>Services / databases</div>
            {SERVICES.map((item) => {
              const active = item.service === selected
              return <button key={item.service} onClick={() => setSelected(item.service)} style={{ width: '100%', textAlign: 'left', border: `1px solid ${active ? '#d4a054' : 'transparent'}`, background: active ? '#1d2530' : 'transparent', color: '#e6edf3', borderRadius: 7, padding: '10px', cursor: 'pointer', marginBottom: 4 }}>{item.service}</button>
            })}
          </aside>

          <div style={{ display: 'grid', gap: 16 }}>
            <section style={{ background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 18 }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h2 style={{ margin: 0, fontSize: 22 }}>{current.service}</h2>
                  <div style={{ color: '#7d8a9c', marginTop: 5 }}>{current.database} · {current.mode}</div>
                </div>
                <CapabilityBadge value={current.genericWrites} />
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 16 }}>{current.capabilities.map((cap) => <span key={cap} style={{ border: '1px solid #2a3341', borderRadius: 999, padding: '5px 9px', fontSize: 11, color: '#e6edf3' }}>{cap}</span>)}</div>
              <div style={{ marginTop: 16, padding: 12, borderRadius: 8, background: 'rgba(248,81,73,0.06)', border: '1px solid rgba(248,81,73,0.25)', color: '#ffb4af', fontSize: 12 }}><strong>Protected boundary:</strong> {current.protected}</div>
            </section>

            {current.service === 'payment-service' && (
              <section style={{ background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 18 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                  <div><h2 style={{ margin: 0, fontSize: 18 }}>Live entity inventory</h2><p style={{ color: '#7d8a9c', fontSize: 12, marginBottom: 0 }}>Read-only inspection through the guarded payment admin adapter.</p></div>
                  <button onClick={inspectPaymentDatabase} disabled={loading} style={{ display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid #d4a054', background: 'rgba(212,160,84,0.12)', color: '#e6edf3', borderRadius: 7, padding: '8px 11px', cursor: loading ? 'not-allowed' : 'pointer' }}><RefreshCw size={14} /> {loading ? 'Inspecting…' : 'Inspect live DB'}</button>
                </div>
                {tables.length > 0 && <div style={{ overflowX: 'auto', marginTop: 14 }}><table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}><thead><tr><th style={th}>Entity</th><th style={th}>Generic write</th><th style={th}>Columns</th><th style={th}>Sensitive</th></tr></thead><tbody>{tables.map((table) => <tr key={table.name}><td style={td}>{table.name}</td><td style={td}>{table.writable ? 'Controlled' : 'No'}</td><td style={td}>{table.columns?.length ?? '—'}</td><td style={td}>{table.read_only ? 'Protected/read-only' : 'Service policy'}</td></tr>)}</tbody></table></div>}
              </section>
            )}

            <section style={{ background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 18 }}>
              <h2 style={{ marginTop: 0, fontSize: 18 }}>Control-plane guarantees</h2>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10 }}>
                {['RBAC + tenant isolation', 'Schema validation + duplicate detection', 'Transactional imports with rollback', 'Bounded CSV / JSON / XLSX export', 'PDF reports + KPI drill-down', 'Auditable destructive operations', 'Named backup + guarded restore', 'HD/4K responsive visualization; 3D only when useful'].map((item) => <div key={item} style={{ padding: 11, border: '1px solid #2a3341', borderRadius: 8, color: '#c7d0db', fontSize: 12 }}>{item}</div>)}
              </div>
              <div style={{ marginTop: 14, color: '#7d8a9c', fontSize: 12, display: 'flex', gap: 7, alignItems: 'center' }}><FileDown size={14} /> Export/report actions are exposed only where the selected adapter and data policy permit them.</div>
            </section>
          </div>
        </section>
      </div>
    </main>
  )
}

function Metric({ icon, label, value }) { return <div style={{ background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 16 }}><div style={{ color: '#7d8a9c', display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>{icon}{label}</div><div style={{ fontSize: 24, fontWeight: 700, marginTop: 8 }}>{value}</div></div> }
function CapabilityBadge({ value }) { const item = STATUS[String(value)] || STATUS.false; return <span style={{ border: `1px solid ${item.tone}`, color: item.tone, borderRadius: 999, padding: '6px 10px', fontSize: 11, whiteSpace: 'nowrap' }}>{item.label}</span> }
const th = { textAlign: 'left', padding: '9px 8px', borderBottom: '1px solid #2a3341', color: '#7d8a9c' }
const td = { padding: '9px 8px', borderBottom: '1px solid #2a3341' }
