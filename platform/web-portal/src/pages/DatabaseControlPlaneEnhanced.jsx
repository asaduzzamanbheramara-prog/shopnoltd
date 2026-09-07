import { useMemo, useState } from 'react'
import { BarChart3, Database, Download, FileDown, FileUp, Lock, RefreshCw, ShieldCheck } from 'lucide-react'

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

function headers() { const token = localStorage.getItem('shopno_token'); return token ? { Authorization: `Bearer ${token}` } : {} }
async function jsonFetch(base, path, options = {}) { const r = await fetch(`${base}${path}`, { ...options, headers: { Accept: 'application/json', ...headers(), ...(options.headers || {}) } }); const text = await r.text(); let data = null; try { data = text ? JSON.parse(text) : null } catch { data = text }; if (!r.ok) throw new Error(data?.detail || data?.message || `HTTP ${r.status}`); return data }
function save(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url) }
function statusLabel(v) { return v === true ? 'Controlled CRUD' : v === 'controlled' ? 'Controlled workflow' : v === 'application' ? 'Application-native' : 'Read-only generic' }

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
  const current = useMemo(() => SERVICES.find(x => x[0] === service) || SERVICES[0], [service])
  const blog = service === 'social/blog'
  const payment = service === 'payment-service'

  async function inspectPayment() {
    setBusy(true); setMessage('')
    try { const data = await jsonFetch(PAYMENT_API, '/api/v1/admin/tables'); setTables(data || []); if (!table && data?.[0]?.name) setTable(data[0].name) }
    catch (e) { setMessage(`Database inspection failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function inspectPaymentTable(name = table) {
    if (!name) return; setBusy(true); setMessage('')
    try { const q = query ? `?limit=${PAGE_SIZE}&offset=0&search=${encodeURIComponent(query)}` : `?limit=${PAGE_SIZE}&offset=0`; const data = await jsonFetch(PAYMENT_API, `/api/v1/admin/tables/${encodeURIComponent(name)}${q}`); setRows(data.rows || []); setAnalysis(await jsonFetch(PAYMENT_API, `/api/v1/admin/tables/${encodeURIComponent(name)}/analysis`)) }
    catch (e) { setMessage(`Entity inspection failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function inspectBlog() { setBusy(true); setMessage(''); try { setAnalysis(await jsonFetch(SOCIAL_API, '/api/v1/admin/blog-data/analysis')); setRows((await jsonFetch(SOCIAL_API, '/api/v1/blog/admin')) || []) } catch (e) { setMessage(`Blog inspection failed: ${e.message}`) } finally { setBusy(false) } }
  async function exportData(format) {
    setBusy(true); setMessage(''); try { const base = blog ? SOCIAL_API : PAYMENT_API; const path = blog ? `/api/v1/admin/blog-data/export?format=${format}` : `/api/v1/admin/tables/${encodeURIComponent(table)}/export?format=${format}`; const r = await fetch(`${base}${path}`, { headers: headers() }); if (!r.ok) throw new Error(`HTTP ${r.status}`); save(await r.blob(), `${blog ? 'blog_posts' : table}.${format}`) } catch (e) { setMessage(`Export failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function readImportPreview(e) {
    const selected = e.target.files?.[0]; setFile(selected || null); setPreview(null); if (!selected) return
    if (blog) { setBusy(true); setMessage(''); try { const form = new FormData(); form.append('file', selected); const data = await jsonFetch(SOCIAL_API, `/api/v1/admin/blog-data/import/preview?operation=${encodeURIComponent(mode)}`, { method: 'POST', body: form }); setPreview(data) } catch (err) { setMessage(`Import validation failed: ${err.message}`) } finally { setBusy(false) } }
  }
  async function commitImport() {
    if (!file || !blog) return; const destructive = mode === 'delete' || mode === 'replace_rows'; if (destructive && !window.confirm(`Confirm ${mode.replace('_', ' ')} for the current tenant?`)) return
    setBusy(true); setMessage(''); try { const form = new FormData(); form.append('file', file); const suffix = destructive ? '&confirm=true' : ''; const result = await jsonFetch(SOCIAL_API, `/api/v1/admin/blog-data/import?operation=${encodeURIComponent(mode)}${suffix}`, { method: 'POST', body: form }); setMessage(`Import committed: ${JSON.stringify(result)}`); setFile(null); setPreview(null); await inspectBlog() } catch (e) { setMessage(`Import failed and was rolled back: ${e.message}`) } finally { setBusy(false) }
  }

  return <main style={page}><div style={wrap}>
    <header style={{ marginBottom: 20 }}><div style={title}><Database size={26} /><h1>Database Control Plane</h1></div><p style={muted}>Capability-driven database operations. Financial, identity, security and audit stores remain protected behind their owning service APIs.</p></header>
    <div style={metricGrid}><Metric icon={<Database size={17} />} label="Data domains" value={SERVICES.length} /><Metric icon={<ShieldCheck size={17} />} label="Protected boundaries" value={SERVICES.filter(x => x[2] !== true).length} /><Metric icon={<Lock size={17} />} label="Generic financial writes" value="0" /><Metric icon={<BarChart3 size={17} />} label="HD / 4K ready" value="Responsive" /></div>
    {message && <div style={notice}>{message}</div>}
    <div style={layout}><aside style={panel}><strong>Services / stores</strong>{SERVICES.map(x => <button key={x[0]} onClick={() => { setService(x[0]); setMessage(''); setRows([]); setAnalysis(null); setTables([]) }} style={{ ...nav, ...(service === x[0] ? active : {}) }}>{x[0]}<small style={{ display: 'block', opacity: .65 }}>{statusLabel(x[2])}</small></button>)}</aside>
      <section style={{ display: 'grid', gap: 14 }}>
        <section style={panel}><div style={between}><div><h2 style={{ margin: 0 }}>{current[0]}</h2><div style={muted}>{current[1]}</div></div><span style={badge}>{statusLabel(current[2])}</span></div><p style={muted}>{current[3]}</p></section>
        {blog && <BlogPanel busy={busy} rows={rows} analysis={analysis} mode={mode} setMode={setMode} file={file} preview={preview} onFile={readImportPreview} onCommit={commitImport} onExport={exportData} onInspect={inspectBlog} />}
        {payment && <PaymentPanel busy={busy} tables={tables} table={table} setTable={setTable} rows={rows} analysis={analysis} query={query} setQuery={setQuery} onInspect={inspectPayment} onInspectTable={inspectPaymentTable} onExport={exportData} />}
        {!blog && !payment && <section style={panel}><h3 style={{ marginTop: 0 }}>Service-owned adapter</h3><p style={muted}>This domain is intentionally not exposed as arbitrary database CRUD. The control plane will surface its validated service API capabilities here without bypassing business rules, tenant isolation or security controls.</p><div style={visualCard}><strong>Visualization contract</strong><p style={muted}>HD and 4K responsive dashboards are supported. 3D is enabled only for multidimensional/temporal/geospatial datasets; ledgers and audit trails remain 2D for accuracy.</p></div></section>}
        {analysis && <Visualization analysis={analysis} />}
      </section></div>
  </div></main>
}

function BlogPanel(p) { return <section style={panel}><div style={between}><div><h3 style={{ margin: 0 }}>Blog data operations</h3><p style={muted}>Round-trip import/export with preview, tenant isolation, transactional rollback and audit.</p></div><button onClick={p.onInspect} disabled={p.busy} style={action}>{p.busy ? 'Loading…' : 'Inspect blog data'}</button></div><div style={buttonRow}>{['json','csv','xlsx','pdf'].map(x => <button key={x} onClick={() => p.onExport(x)} style={small}><Download size={13} /> {x.toUpperCase()}</button>)}<label style={small}><FileUp size={13} /> Import<input type="file" accept=".csv,.json,.xlsx" onChange={p.onFile} hidden /></label></div><div style={buttonRow}>{MODES.map(([v, l]) => <button key={v} onClick={() => p.setMode(v)} style={{ ...small, ...(p.mode === v ? selected : {}) }}>{l}</button>)}</div>{p.mode === 'create_table' && <div style={notice}>Create-table is shown in the common contract but BlogPost schema is service-owned; schema replacement is intentionally denied.</div>}{p.preview && <pre style={pre}>{JSON.stringify(p.preview, null, 2)}</pre>}{p.file && <div style={between}><span>{p.file.name}</span><button onClick={p.onCommit} disabled={!p.preview || p.busy} style={action}><FileUp size={13} /> Commit transaction</button></div>}</section> }
function PaymentPanel(p) { return <section style={panel}><div style={between}><div><h3 style={{ margin: 0 }}>Protected payment database</h3><p style={muted}>Inspection/export/reporting are available; generic money-moving mutation remains disabled.</p></div><button onClick={p.onInspect} disabled={p.busy} style={action}><RefreshCw size={13} /> Inspect</button></div>{p.tables.length > 0 && <div style={scroll}><table style={tableStyle}><thead><tr><th>Entity</th><th>Write</th><th>Columns</th><th>Sensitive</th></tr></thead><tbody>{p.tables.map(t => <tr key={t.name} onClick={() => { p.setTable(t.name); p.onInspectTable(t.name) }}><td>{t.name}</td><td>{t.writable ? 'Controlled' : 'No'}</td><td>{t.columns?.length ?? '—'}</td><td>{t.financially_sensitive ? 'Protected' : 'Policy'}</td></tr>)}</tbody></table></div>}{p.table && <><div style={buttonRow}>{['json','csv','xlsx'].map(x => <button key={x} onClick={() => p.onExport(x)} style={small}><Download size={13} /> {x.toUpperCase()}</button>)}</div><form onSubmit={e => { e.preventDefault(); p.onInspectTable() }} style={buttonRow}><input value={p.query} onChange={e => p.setQuery(e.target.value)} placeholder="Search all columns…" style={input} /><button style={action}>Search</button></form></>}</section> }
function Visualization({ analysis }) { const status = analysis.status_distribution || {}; const values = Object.entries(status); const max = Math.max(1, ...values.map(x => x[1])); return <section style={panel}><div className="db-viz" style={viz}><div><h3 style={{ margin: 0 }}>HD / 4K analysis view</h3><p style={muted}>Responsive 2D distribution plus CSS 3D depth view where multidimensional data is meaningful.</p></div><div style={bars}>{values.map(([k, v]) => <div key={k} style={barItem}><span>{k}: {v}</span><div style={{ ...bar, width: `${Math.max(4, v / max * 100)}%` }} /></div>)}</div><div style={threeD}><div style={cubeTop} /><div style={cubeFront}><strong>3D</strong><span>{analysis.rows ?? 0} rows</span></div></div></section> }
function Metric({ icon, label, value }) { return <div style={metric}><div>{icon}</div><small>{label}</small><strong>{value}</strong></div> }
const page={minHeight:'calc(100vh - 64px)',background:'#0f1419',color:'#e6edf3',padding:'clamp(14px,3vw,36px)'}; const wrap={maxWidth:1600,margin:'0 auto'}; const title={display:'flex',alignItems:'center',gap:10}; const muted={color:'#9da7b3',marginTop:6}; const metricGrid={display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:10,marginBottom:14}; const metric={background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:14,display:'grid',gap:5}; const layout={display:'grid',gridTemplateColumns:'minmax(220px,300px) minmax(0,1fr)',gap:14}; const panel={background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:16}; const between={display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'}; const nav={display:'block',width:'100%',textAlign:'left',padding:'9px 10px',marginTop:5,border:0,borderRadius:7,background:'transparent',color:'#d8dee6',cursor:'pointer'}; const active={background:'#243244'}; const badge={padding:'5px 8px',borderRadius:999,border:'1px solid #3a4655',fontSize:12}; const action={display:'inline-flex',alignItems:'center',gap:6,padding:'8px 11px',borderRadius:7,border:'1px solid #3a4655',background:'#1e2935',color:'#fff',cursor:'pointer'}; const small={...action,padding:'6px 9px',fontSize:12}; const selected={borderColor:'#d4a054',background:'#2b251a'}; const buttonRow={display:'flex',flexWrap:'wrap',gap:7,marginTop:12}; const notice={padding:10,margin:'10px 0',border:'1px solid #5b4726',background:'#201b13',borderRadius:7,color:'#e5c78d',overflowWrap:'anywhere'}; const pre={maxHeight:300,overflow:'auto',background:'#0b0f14',padding:10,borderRadius:7,fontSize:12}; const input={flex:1,minWidth:180,padding:9,borderRadius:7,border:'1px solid #374151',background:'#0c1117',color:'#fff'}; const scroll={overflowX:'auto',marginTop:12}; const tableStyle={width:'100%',borderCollapse:'collapse'}; const visualCard={marginTop:10,padding:12,border:'1px solid #2b3642',borderRadius:8}; const viz={overflow:'hidden'}; const bars={display:'grid',gap:8,marginTop:14}; const barItem={display:'grid',gap:4,fontSize:12}; const bar={height:10,borderRadius:5,background:'#5d86b3'}; const threeD={marginTop:20,minHeight:130,position:'relative',perspective:700,display:'flex',alignItems:'center',justifyContent:'center',background:'#0c1117',borderRadius:8}; const cubeFront={width:140,height:70,display:'flex',alignItems:'center',justifyContent:'center',gap:8,flexDirection:'column',border:'1px solid #6c7d90',transform:'rotateX(-12deg) rotateY(22deg)',boxShadow:'18px 12px 0 rgba(108,125,144,.18)'}; const cubeTop={position:'absolute',width:140,height:30,border:'1px solid #6c7d90',transform:'translateY(-49px) rotateX(58deg) rotateY(22deg)'};
