import { useMemo, useState } from 'react'
import { BarChart3, Database, Download, FileUp, Lock, RefreshCw, ShieldCheck } from 'lucide-react'

const PAYMENT_API = import.meta.env.VITE_PAYMENT_API_URL || 'https://payment-service.shopnoltd.dpdns.org'
const SOCIAL_API = import.meta.env.VITE_SOCIAL_API_URL || 'https://social-service.shopnoltd.dpdns.org'
const PAGE_SIZE = 50
const MODES = [
  ['add', 'Add rows'], ['update', 'Update matching rows'], ['upsert', 'Upsert'], ['merge', 'Merge'],
  ['delete', 'Delete matching rows'], ['replace_rows', 'Replace rows'], ['create_table', 'Create/import as new table'],
]
const SERVICES = [
  ['payment-service', 'Financial PostgreSQL', false, 'Service-owned money state; generic writes disabled.'],
  ['billing-engine', 'Billing PostgreSQL', false, 'Ledger and billing mutations use validated service APIs.'],
  ['exchange-service', 'Exchange PostgreSQL', false, 'Rate/provider history remains service-owned.'],
  ['auth-service / Keycloak', 'Identity store', false, 'Identity, roles, credentials and sessions remain protected.'],
  ['domain-service', 'Domain PostgreSQL', 'controlled', 'Registration, renewal, registrar and billing changes use workflows.'],
  ['freedomain-service', 'Tenant/domain PostgreSQL', 'controlled', 'DNS and tenant lifecycle remain workflow-controlled.'],
  ['ai-platform', 'AI PostgreSQL', 'controlled', 'Provider/model lifecycle is controlled and secrets are never exported.'],
  ['social/blog', 'Content PostgreSQL', true, 'Blog content supports guarded CRUD and round-trip data operations.'],
  ['analytics-service', 'Analytics store', 'controlled', 'Datasets and queries remain service-owned.'],
  ['KoboToolbox / KoBoCat / Enketo', 'Application stores', 'application', 'Use application-native APIs for forms/submissions.'],
  ['mail / meeting / storage', 'Application metadata', 'application', 'Use application/service APIs; secrets remain protected.'],
  ['audit-service', 'Append-only audit store', false, 'Historical audit records are immutable.'],
]

function authHeaders() {
  const token = localStorage.getItem('shopno_token')
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function jsonFetch(base, path, options = {}) {
  const response = await fetch(`${base}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...authHeaders(), ...(options.headers || {}) },
  })
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `HTTP ${response.status}`)
  return data
}

function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function statusLabel(value) {
  if (value === true) return 'Controlled CRUD'
  if (value === 'controlled') return 'Controlled workflow'
  if (value === 'application') return 'Application-native'
  return 'Read-only generic'
}

export default function DatabaseControlPlaneEnhanced() {
  const [service, setService] = useState('social/blog')
  const [tables, setTables] = useState([])
  const [table, setTable] = useState('')
  const [rows, setRows] = useState([])
  const [analysis, setAnalysis] = useState(null)
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('add')
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const current = useMemo(() => SERVICES.find(item => item[0] === service) || SERVICES[0], [service])
  const blog = service === 'social/blog'
  const payment = service === 'payment-service'

  const inspectPayment = async () => {
    setBusy(true); setMessage('')
    try {
      const data = await jsonFetch(PAYMENT_API, '/api/v1/admin/tables')
      setTables(data || [])
      if (!table && data?.[0]?.name) setTable(data[0].name)
    } catch (error) { setMessage(`Database inspection failed: ${error.message}`) }
    finally { setBusy(false) }
  }

  const inspectPaymentTable = async (name = table) => {
    if (!name) return
    setBusy(true); setMessage('')
    try {
      const suffix = query ? `?limit=${PAGE_SIZE}&offset=0&search=${encodeURIComponent(query)}` : `?limit=${PAGE_SIZE}&offset=0`
      const data = await jsonFetch(PAYMENT_API, `/api/v1/admin/tables/${encodeURIComponent(name)}${suffix}`)
      setRows(data.rows || [])
      setAnalysis(await jsonFetch(PAYMENT_API, `/api/v1/admin/tables/${encodeURIComponent(name)}/analysis`))
    } catch (error) { setMessage(`Entity inspection failed: ${error.message}`) }
    finally { setBusy(false) }
  }

  const inspectBlog = async () => {
    setBusy(true); setMessage('')
    try {
      const [analysisData, rowData] = await Promise.all([
        jsonFetch(SOCIAL_API, '/api/v1/admin/blog-data/analysis'),
        jsonFetch(SOCIAL_API, '/api/v1/blog/admin'),
      ])
      setAnalysis(analysisData)
      setRows(rowData || [])
    } catch (error) { setMessage(`Blog inspection failed: ${error.message}`) }
    finally { setBusy(false) }
  }

  const exportData = async format => {
    if (!blog && !table) return
    setBusy(true); setMessage('')
    try {
      const base = blog ? SOCIAL_API : PAYMENT_API
      const path = blog
        ? `/api/v1/admin/blog-data/export?format=${format}`
        : `/api/v1/admin/tables/${encodeURIComponent(table)}/export?format=${format}`
      const response = await fetch(`${base}${path}`, { headers: authHeaders() })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      saveBlob(await response.blob(), `${blog ? 'blog_posts' : table}.${format}`)
    } catch (error) { setMessage(`Export failed: ${error.message}`) }
    finally { setBusy(false) }
  }

  const readImportPreview = async event => {
    const selected = event.target.files?.[0]
    setFile(selected || null); setPreview(null)
    if (!selected || !blog) return
    setBusy(true); setMessage('')
    try {
      const form = new FormData(); form.append('file', selected)
      setPreview(await jsonFetch(SOCIAL_API, `/api/v1/admin/blog-data/import/preview?operation=${encodeURIComponent(mode)}`, { method: 'POST', body: form }))
    } catch (error) { setMessage(`Import validation failed: ${error.message}`) }
    finally { setBusy(false) }
  }

  const commitImport = async () => {
    if (!file || !blog || !preview) return
    const destructive = mode === 'delete' || mode === 'replace_rows'
    if (destructive && !window.confirm(`Confirm ${mode.replace('_', ' ')} for the current tenant?`)) return
    setBusy(true); setMessage('')
    try {
      const form = new FormData(); form.append('file', file)
      const suffix = destructive ? '&confirm=true' : ''
      const result = await jsonFetch(SOCIAL_API, `/api/v1/admin/blog-data/import?operation=${encodeURIComponent(mode)}${suffix}`, { method: 'POST', body: form })
      setMessage(`Import committed: ${JSON.stringify(result)}`)
      setFile(null); setPreview(null)
      await inspectBlog()
    } catch (error) { setMessage(`Import failed and was rolled back: ${error.message}`) }
    finally { setBusy(false) }
  }

  const selectService = name => {
    setService(name); setMessage(''); setRows([]); setAnalysis(null); setTables([]); setTable(''); setFile(null); setPreview(null)
  }

  return (
    <main style={styles.page}><div style={styles.wrap}>
      <header style={{ marginBottom: 20 }}>
        <div style={styles.title}><Database size={26} /><h1>Database Control Plane</h1></div>
        <p style={styles.muted}>Capability-driven operations. Financial, identity, security and audit stores remain protected behind their owning service APIs.</p>
      </header>
      <div style={styles.metricGrid}>
        <Metric icon={<Database size={17} />} label="Data domains" value={SERVICES.length} />
        <Metric icon={<ShieldCheck size={17} />} label="Protected boundaries" value={SERVICES.filter(item => item[2] !== true).length} />
        <Metric icon={<Lock size={17} />} label="Generic financial writes" value="0" />
        <Metric icon={<BarChart3 size={17} />} label="HD / 4K ready" value="Responsive" />
      </div>
      {message && <div style={styles.notice}>{message}</div>}
      <div style={styles.layout}>
        <aside style={styles.panel}><strong>Services / stores</strong>{SERVICES.map(item => (
          <button key={item[0]} onClick={() => selectService(item[0])} style={{ ...styles.nav, ...(service === item[0] ? styles.active : {}) }}>
            {item[0]}<small style={{ display: 'block', opacity: .65 }}>{statusLabel(item[2])}</small>
          </button>
        ))}</aside>
        <section style={{ display: 'grid', gap: 14 }}>
          <section style={styles.panel}><div style={styles.between}><div><h2 style={{ margin: 0 }}>{current[0]}</h2><div style={styles.muted}>{current[1]}</div></div><span style={styles.badge}>{statusLabel(current[2])}</span></div><p style={styles.muted}>{current[3]}</p></section>
          {blog && <BlogPanel {...{ busy, rows, analysis, mode, setMode, file, preview, onFile: readImportPreview, onCommit: commitImport, onExport: exportData, onInspect: inspectBlog }} />}
          {payment && <PaymentPanel {...{ busy, tables, table, setTable, rows, analysis, query, setQuery, onInspect: inspectPayment, onInspectTable: inspectPaymentTable, onExport: exportData }} />}
          {!blog && !payment && <section style={styles.panel}><h3 style={{ marginTop: 0 }}>Service-owned adapter</h3><p style={styles.muted}>This domain is not exposed as arbitrary database CRUD. Validated service APIs preserve business rules, tenant isolation and security controls.</p><div style={styles.visualCard}><strong>Visualization contract</strong><p style={styles.muted}>HD and 4K responsive dashboards are supported. 3D is enabled only for multidimensional, temporal or geospatial datasets; ledgers and audit trails remain 2D for accuracy.</p></div></section>}
          {analysis && <Visualization analysis={analysis} />}
          {rows.length > 0 && <RowsPreview rows={rows} />}
        </section>
      </div>
    </div></main>
  )
}

function BlogPanel({ busy, mode, setMode, file, preview, onFile, onCommit, onExport, onInspect }) {
  return <section style={styles.panel}>
    <div style={styles.between}><div><h3 style={{ margin: 0 }}>Blog data operations</h3><p style={styles.muted}>Round-trip import/export with preview, tenant isolation, transactional rollback and audit.</p></div><button onClick={onInspect} disabled={busy} style={styles.action}>{busy ? 'Loading…' : 'Inspect blog data'}</button></div>
    <div style={styles.buttonRow}>{['json', 'csv', 'xlsx', 'pdf'].map(format => <button key={format} onClick={() => onExport(format)} style={styles.small}><Download size={13} /> {format.toUpperCase()}</button>)}<label style={styles.small}><FileUp size={13} /> Import<input type="file" accept=".csv,.json,.xlsx" onChange={onFile} hidden /></label></div>
    <div style={styles.buttonRow}>{MODES.map(([value, label]) => <button key={value} onClick={() => setMode(value)} style={{ ...styles.small, ...(mode === value ? styles.selected : {}) }}>{label}</button>)}</div>
    {mode === 'create_table' && <div style={styles.notice}>Create-table is shown in the common contract, but BlogPost schema is service-owned; schema replacement is intentionally denied.</div>}
    {preview && <pre style={styles.pre}>{JSON.stringify(preview, null, 2)}</pre>}
    {file && <div style={styles.between}><span>{file.name}</span><button onClick={onCommit} disabled={!preview || busy} style={styles.action}><FileUp size={13} /> Commit transaction</button></div>}
  </section>
}

function PaymentPanel({ busy, tables, table, setTable, query, setQuery, onInspect, onInspectTable, onExport }) {
  return <section style={styles.panel}>
    <div style={styles.between}><div><h3 style={{ margin: 0 }}>Protected payment database</h3><p style={styles.muted}>Inspection/export/reporting are available; generic money-moving mutation remains disabled.</p></div><button onClick={onInspect} disabled={busy} style={styles.action}><RefreshCw size={13} /> Inspect</button></div>
    {tables.length > 0 && <div style={styles.scroll}><table style={styles.table}><thead><tr><th>Entity</th><th>Write</th><th>Columns</th><th>Sensitive</th></tr></thead><tbody>{tables.map(item => <tr key={item.name} onClick={() => { setTable(item.name); onInspectTable(item.name) }}><td>{item.name}</td><td>{item.writable ? 'Controlled' : 'No'}</td><td>{item.columns?.length ?? '—'}</td><td>{item.financially_sensitive ? 'Protected' : 'Policy'}</td></tr>)}</tbody></table></div>}
    {table && <><div style={styles.buttonRow}>{['json', 'csv', 'xlsx'].map(format => <button key={format} onClick={() => onExport(format)} style={styles.small}><Download size={13} /> {format.toUpperCase()}</button>)}</div><form onSubmit={event => { event.preventDefault(); onInspectTable() }} style={styles.buttonRow}><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search all columns…" style={styles.input} /><button style={styles.action}>Search</button></form></>}
  </section>
}

function Visualization({ analysis }) {
  const status = analysis.status_distribution || {}
  const values = Object.entries(status).filter(([, value]) => Number.isFinite(Number(value)))
  const max = Math.max(1, ...values.map(([, value]) => Number(value)))
  return <section style={styles.panel}>
    <h3 style={{ margin: 0 }}>HD / 4K analysis view</h3><p style={styles.muted}>Responsive distribution plus a CSS 3D depth view where multidimensional data is meaningful.</p>
    <div style={styles.bars}>{values.map(([key, value]) => <div key={key} style={styles.barItem}><span>{key}: {value}</span><div style={{ ...styles.bar, width: `${Math.max(4, Number(value) / max * 100)}%` }} /></div>)}</div>
    <div style={styles.threeD}><div style={styles.cubeTop} /><div style={styles.cubeFront}><strong>3D</strong><span>{analysis.rows ?? 0} rows</span></div></div>
  </section>
}

function RowsPreview({ rows }) {
  const columns = Object.keys(rows[0] || {}).slice(0, 8)
  return <section style={styles.panel}><h3 style={{ marginTop: 0 }}>Entity preview</h3><div style={styles.scroll}><table style={styles.table}><thead><tr>{columns.map(column => <th key={column}>{column}</th>)}</tr></thead><tbody>{rows.slice(0, 20).map((row, index) => <tr key={row.id ?? index}>{columns.map(column => <td key={column}>{String(row[column] ?? '')}</td>)}</tr>)}</tbody></table></div></section>
}

function Metric({ icon, label, value }) { return <div style={styles.metric}><div>{icon}</div><small>{label}</small><strong>{value}</strong></div> }

const styles = {
  page: { minHeight: 'calc(100vh - 64px)', background: '#0f1419', color: '#e6edf3', padding: 'clamp(14px,3vw,36px)' },
  wrap: { maxWidth: 1600, margin: '0 auto' }, title: { display: 'flex', alignItems: 'center', gap: 10 },
  muted: { color: '#9da7b3', marginTop: 6 }, metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10, marginBottom: 14 },
  metric: { background: '#151b22', border: '1px solid #27303b', borderRadius: 10, padding: 14, display: 'grid', gap: 5 },
  layout: { display: 'grid', gridTemplateColumns: 'minmax(220px,300px) minmax(0,1fr)', gap: 14 },
  panel: { background: '#151b22', border: '1px solid #27303b', borderRadius: 10, padding: 16 },
  between: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 10, flexWrap: 'wrap' }, nav: { display: 'block', width: '100%', textAlign: 'left', padding: '9px 10px', marginTop: 5, border: 0, borderRadius: 7, background: 'transparent', color: '#d8dee6', cursor: 'pointer' }, active: { background: '#243244' },
  badge: { padding: '5px 8px', borderRadius: 999, border: '1px solid #3a4655', fontSize: 12 }, action: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '8px 11px', borderRadius: 7, border: '1px solid #3a4655', background: '#1e2935', color: '#fff', cursor: 'pointer' },
  small: { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '6px 9px', borderRadius: 7, border: '1px solid #3a4655', background: '#1e2935', color: '#fff', cursor: 'pointer', fontSize: 12 }, selected: { borderColor: '#d4a054', background: '#2b251a' },
  buttonRow: { display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 12 }, notice: { padding: 10, margin: '10px 0', border: '1px solid #5b4726', background: '#201b13', borderRadius: 7, color: '#e5c78d', overflowWrap: 'anywhere' },
  pre: { maxHeight: 300, overflow: 'auto', background: '#0b0f14', padding: 10, borderRadius: 7, fontSize: 12 }, input: { flex: 1, minWidth: 180, padding: 9, borderRadius: 7, border: '1px solid #3a4655', background: '#0b0f14', color: '#fff' }, scroll: { overflowX: 'auto', marginTop: 12 }, table: { width: '100%', borderCollapse: 'collapse', fontSize: 13 },
  visualCard: { marginTop: 12, padding: 14, borderRadius: 8, border: '1px solid #2d3946' }, bars: { display: 'grid', gap: 8, marginTop: 14 }, barItem: { display: 'grid', gap: 4, fontSize: 12 }, bar: { height: 9, minWidth: 4, borderRadius: 99, background: '#718096' }, threeD: { position: 'relative', width: 150, height: 100, marginTop: 20, transform: 'perspective(500px) rotateX(58deg) rotateZ(-18deg)', transformOrigin: 'center', border: '1px solid #3a4655' }, cubeTop: { position: 'absolute', inset: 0, background: '#263445', transform: 'translateZ(24px)' }, cubeFront: { position: 'absolute', left: 18, top: 18, width: 110, height: 64, display: 'grid', placeItems: 'center', background: '#1e2935', border: '1px solid #526070', boxShadow: '10px 10px 0 rgba(0,0,0,.22)' },
}
