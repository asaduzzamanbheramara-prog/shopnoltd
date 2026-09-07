import { useMemo, useState } from 'react'
import { BarChart3, Database, Download, FileDown, Lock, RefreshCw, Search, ShieldCheck } from 'lucide-react'

const PAYMENT_API = import.meta.env.VITE_PAYMENT_API_URL || 'https://payment-service.shopnoltd.dpdns.org'
const PAGE_SIZE = 50

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

async function api(path, options = {}) {
  const response = await fetch(`${PAYMENT_API}${path}`, { ...options, headers: { Accept: 'application/json', ...authHeaders(), ...(options.headers || {}) } })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `HTTP ${response.status}`)
  return data
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
}

export default function DatabaseControlPlane() {
  const [selected, setSelected] = useState(SERVICES[0].service)
  const [tables, setTables] = useState([])
  const [tableName, setTableName] = useState('')
  const [rows, setRows] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const current = useMemo(() => SERVICES.find((item) => item.service === selected) || SERVICES[0], [selected])
  const selectedMeta = useMemo(() => tables.find((item) => item.name === tableName), [tables, tableName])

  async function inspectPaymentDatabase() {
    setLoading(true); setError('')
    try {
      const data = await api('/api/v1/admin/tables')
      const list = Array.isArray(data) ? data : []
      setTables(list)
      if (!tableName && list[0]?.name) setTableName(list[0].name)
    } catch (err) { setError(`Payment database inspection failed: ${err.message}`) } finally { setLoading(false) }
  }

  async function inspectTable(name = tableName, nextOffset = offset, term = search) {
    if (!name) return
    setLoading(true); setError('')
    try {
      const qs = new URLSearchParams({ limit: String(PAGE_SIZE), offset: String(nextOffset) })
      if (term) qs.set('search', term)
      const data = await api(`/api/v1/admin/tables/${encodeURIComponent(name)}?${qs}`)
      setRows(data?.rows || []); setOffset(nextOffset)
      const a = await api(`/api/v1/admin/tables/${encodeURIComponent(name)}/analysis`)
      setAnalysis(a)
    } catch (err) { setError(`Entity inspection failed: ${err.message}`) } finally { setLoading(false) }
  }

  async function exportTable(format) {
    if (!tableName) return
    setLoading(true); setError('')
    try {
      const qs = new URLSearchParams({ format })
      if (search) qs.set('search', search)
      const response = await fetch(`${PAYMENT_API}/api/v1/admin/tables/${encodeURIComponent(tableName)}/export?${qs}`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      downloadBlob(await response.blob(), `${tableName}.${format}`)
    } catch (err) { setError(`Export failed: ${err.message}`) } finally { setLoading(false) }
  }

  async function reportTable(format) {
    if (!tableName) return
    setLoading(true); setError('')
    try {
      const response = await fetch(`${PAYMENT_API}/api/v1/admin/data-reports/${encodeURIComponent(tableName)}/${format}`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      downloadBlob(await response.blob(), `${tableName}.${format}`)
    } catch (err) { setError(`Report generation failed: ${err.message}`) } finally { setLoading(false) }
  }

  function selectTable(name) { setTableName(name); setOffset(0); setSearch(''); setRows([]); setAnalysis(null); inspectTable(name, 0, '') }

  return (
    <main style={{ minHeight: 'calc(100vh - 64px)', background: '#0f1419', color: '#e6edf3', padding: 'clamp(16px, 3vw, 32px)' }}>
      <div style={{ maxWidth: 1500, margin: '0 auto' }}>
        <header style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 8 }}><Database size={24} color="#d4a054" /><h1 style={{ margin: 0, fontSize: 'clamp(24px, 4vw, 36px)' }}>Database Control Plane</h1></div>
          <p style={{ color: '#7d8a9c', maxWidth: 900, lineHeight: 1.6, margin: 0 }}>Cross-service inventory with guarded inspection, analysis, export and reporting. Protected financial, identity, audit and security entities remain behind their owning service APIs.</p>
        </header>

        <section style={grid4}>
          <Metric icon={<Database size={18} />} label="Data domains" value={SERVICES.length} />
          <Metric icon={<ShieldCheck size={18} />} label="Controlled boundaries" value={SERVICES.filter((x) => x.genericWrites !== true).length} />
          <Metric icon={<Lock size={18} />} label="Generic financial writes" value="0" />
          <Metric icon={<BarChart3 size={18} />} label="Analysis/reporting" value="Enabled" />
        </section>

        {error && <div style={errorBox}>{error}</div>}

        <section style={{ display: 'grid', gridTemplateColumns: 'minmax(240px,320px) minmax(0,1fr)', gap: 16, alignItems: 'start' }}>
          <aside style={panel}>
            <div style={labelStyle}>Services / databases</div>
            {SERVICES.map((item) => <button key={item.service} onClick={() => setSelected(item.service)} style={{ ...navButton, ...(item.service === selected ? activeNav : {}) }}>{item.service}</button>)}
          </aside>

          <div style={{ display: 'grid', gap: 16 }}>
            <section style={panel}>
              <div style={rowBetween}><div><h2 style={{ margin: 0, fontSize: 22 }}>{current.service}</h2><div style={{ color: '#7d8a9c', marginTop: 5 }}>{current.database} · {current.mode}</div></div><CapabilityBadge value={current.genericWrites} /></div>
              <div style={chips}>{current.capabilities.map((cap) => <span key={cap} style={chip}>{cap}</span>)}</div>
              <div style={protectedBox}><strong>Protected boundary:</strong> {current.protected}</div>
            </section>

            {current.service === 'payment-service' && (
              <section style={panel}>
                <div style={rowBetween}>
                  <div><h2 style={{ margin: 0, fontSize: 18 }}>Live entity inventory</h2><p style={muted}>Guarded read/analysis/export adapter. Generic money-moving writes are intentionally disabled.</p></div>
                  <button onClick={inspectPaymentDatabase} disabled={loading} style={actionButton}><RefreshCw size={14} /> {loading ? 'Inspecting…' : 'Inspect live DB'}</button>
                </div>
                {tables.length > 0 && <div style={{ overflowX: 'auto', marginTop: 14 }}><table style={tableStyle}><thead><tr><th style={th}>Entity</th><th style={th}>Write</th><th style={th}>Columns</th><th style={th}>Sensitive</th></tr></thead><tbody>{tables.map((table) => <tr key={table.name} onClick={() => selectTable(table.name)} style={{ cursor: 'pointer' }}><td style={td}>{table.name}</td><td style={td}>{table.writable ? 'Controlled' : 'No'}</td><td style={td}>{table.columns?.length ?? '—'}</td><td style={td}>{table.read_only ? 'Protected' : 'Policy'}</td></tr>)}</tbody></table></div>}
              </section>
            )}

            {current.service === 'payment-service' && tableName && (
              <section style={panel}>
                <div style={rowBetween}>
                  <div><h2 style={{ margin: 0, fontSize: 18 }}>{tableName}</h2><div style={muted}>{selectedMeta?.columns?.length || 0} columns · {analysis?.rows ?? '—'} rows</div></div>
                  <div style={buttonGroup}><button onClick={() => exportTable('json')} style={smallButton}><Download size={13} /> JSON</button><button onClick={() => exportTable('csv')} style={smallButton}><Download size={13} /> CSV</button><button onClick={() => exportTable('xlsx')} style={smallButton}><Download size={13} /> XLSX</button><button onClick={() => reportTable('pdf')} style={smallButton}><FileDown size={13} /> PDF</button></div>
                </div>
                <form onSubmit={(e) => { e.preventDefault(); inspectTable(tableName, 0, search) }} style={{ display: 'flex', gap: 8, marginTop: 14 }}><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search all columns…" style={input} /><button type="submit" style={actionButton}><Search size={14} /> Search</button></form>
                {analysis && <div style={{ ...grid4, marginTop: 12 }}><MiniStat label="Rows" value={analysis.rows} /><MiniStat label="Columns" value={analysis.columns} /><MiniStat label="Primary key" value={analysis.primary_key?.join(', ') || 'None'} /><MiniStat label="Unique constraints" value={analysis.unique_constraints?.length ?? 0} /></div>}
                <div style={{ overflowX: 'auto', marginTop: 14 }}>{rows.length ? <table style={tableStyle}><thead><tr>{Object.keys(rows[0]).map((key) => <th key={key} style={th}>{key}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{Object.keys(rows[0]).map((key) => <td key={key} style={td}>{String(row[key] ?? '')}</td>)}</tr>)}</tbody></table> : <div style={muted}>Select an entity and inspect it to load rows.</div>}</div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 12 }}><button disabled={offset === 0 || loading} onClick={() => inspectTable(tableName, Math.max(0, offset - PAGE_SIZE), search)} style={smallButton}>Previous</button><span style={muted}>Rows {offset + 1}–{offset + rows.length}</span><button disabled={rows.length < PAGE_SIZE || loading} onClick={() => inspectTable(tableName, offset + PAGE_SIZE, search)} style={smallButton}>Next</button></div>
              </section>
            )}

            <section style={panel}><h2 style={{ marginTop: 0, fontSize: 18 }}>Control-plane guarantees</h2><div style={gridCards}>{['RBAC + tenant isolation', 'Schema validation + duplicate detection', 'Transactional imports with rollback', 'Bounded CSV / JSON / XLSX export', 'PDF reports + KPI drill-down', 'Auditable destructive operations', 'Named backup + guarded restore', 'HD/4K responsive visualization; 3D only when useful'].map((item) => <div key={item} style={card}>{item}</div>)}</div><div style={muted}><FileDown size={14} style={{ verticalAlign: 'middle' }} /> Export/report actions are exposed only where the selected adapter permits them.</div></section>
          </div>
        </section>
      </div>
    </main>
  )
}

function Metric({ icon, label, value }) { return <div style={metric}><div style={{ color: '#7d8a9c', display: 'flex', gap: 8, alignItems: 'center', fontSize: 12 }}>{icon}{label}</div><div style={{ fontSize: 24, fontWeight: 700, marginTop: 8 }}>{value}</div></div> }
function MiniStat({ label, value }) { return <div style={{ ...metric, padding: 10 }}><div style={muted}>{label}</div><div style={{ marginTop: 5, fontWeight: 700, fontSize: 14 }}>{String(value)}</div></div> }
function CapabilityBadge({ value }) { const item = STATUS[String(value)] || STATUS.false; return <span style={{ border: `1px solid ${item.tone}`, color: item.tone, borderRadius: 999, padding: '6px 10px', fontSize: 11, whiteSpace: 'nowrap' }}>{item.label}</span> }

const panel = { background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 18 }
const metric = { background: '#161c24', border: '1px solid #2a3341', borderRadius: 10, padding: 16 }
const grid4 = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12, marginBottom: 20 }
const gridCards = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 10, marginBottom: 14 }
const card = { padding: 11, border: '1px solid #2a3341', borderRadius: 8, color: '#c7d0db', fontSize: 12 }
const labelStyle = { color: '#7d8a9c', fontSize: 11, textTransform: 'uppercase', letterSpacing: 0.8, padding: '8px 10px' }
const navButton = { width: '100%', textAlign: 'left', border: '1px solid transparent', background: 'transparent', color: '#e6edf3', borderRadius: 7, padding: '10px', cursor: 'pointer', marginBottom: 4 }
const activeNav = { borderColor: '#d4a054', background: '#1d2530' }
const rowBetween = { display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', justifyContent: 'space-between' }
const chips = { display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 16 }
const chip = { border: '1px solid #2a3341', borderRadius: 999, padding: '5px 9px', fontSize: 11 }
const protectedBox = { marginTop: 16, padding: 12, borderRadius: 8, background: 'rgba(248,81,73,0.06)', border: '1px solid rgba(248,81,73,0.25)', color: '#ffb4af', fontSize: 12 }
const actionButton = { display: 'inline-flex', alignItems: 'center', gap: 7, border: '1px solid #d4a054', background: 'rgba(212,160,84,0.12)', color: '#e6edf3', borderRadius: 7, padding: '8px 11px', cursor: 'pointer' }
const smallButton = { display: 'inline-flex', alignItems: 'center', gap: 5, border: '1px solid #2a3341', background: '#1d2530', color: '#e6edf3', borderRadius: 7, padding: '7px 9px', cursor: 'pointer' }
const buttonGroup = { display: 'flex', flexWrap: 'wrap', gap: 6 }
const input = { flex: 1, minWidth: 160, border: '1px solid #2a3341', background: '#0f1419', color: '#e6edf3', borderRadius: 7, padding: '9px 10px' }
const muted = { color: '#7d8a9c', fontSize: 12, lineHeight: 1.5, margin: '5px 0 0' }
const errorBox = { padding: 12, marginBottom: 16, border: '1px solid #f85149', borderRadius: 8, color: '#ffb4af' }
const tableStyle = { width: '100%', borderCollapse: 'collapse', fontSize: 12 }
const th = { textAlign: 'left', padding: '9px 8px', borderBottom: '1px solid #2a3341', color: '#7d8a9c', whiteSpace: 'nowrap' }
const td = { padding: '9px 8px', borderBottom: '1px solid #2a3341', whiteSpace: 'nowrap' }
