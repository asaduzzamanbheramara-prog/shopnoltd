import { useEffect, useMemo, useState } from 'react'
import { BarChart3, Database, Download, FileUp, Lock, RefreshCw, ShieldCheck } from 'lucide-react'

const PAGE_SIZE = 50
const SERVICES = [
  ['payment-service', 'Financial PostgreSQL', 'readonly'], ['billing-engine', 'Billing PostgreSQL', 'protected'],
  ['exchange-service', 'Exchange PostgreSQL', 'protected'], ['auth-service / Keycloak', 'Identity store', 'protected'],
  ['domain-service', 'Domain PostgreSQL', 'workflow'], ['freedomain-service', 'Tenant/domain PostgreSQL', 'workflow'],
  ['ai-platform', 'AI PostgreSQL', 'workflow'], ['social/blog', 'Content PostgreSQL', 'crud'],
  ['analytics-service', 'Analytics store', 'workflow'], ['KoboToolbox / KoBoCat / Enketo', 'Application stores', 'application'],
  ['mail / meeting / storage', 'Application metadata', 'application'], ['audit-service', 'Append-only audit store', 'readonly'],
]
const MODES = [['add', 'Add rows'], ['update', 'Update matching rows'], ['upsert', 'Upsert'], ['merge', 'Merge'], ['delete', 'Delete matching rows'], ['replace_rows', 'Replace rows'], ['create_table', 'Create/import as new table']]

function authHeaders(extra = {}) {
  const token = localStorage.getItem('shopno_token')
  return { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra }
}
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: authHeaders(options.headers || {}) })
  const text = await response.text(); let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || text || `HTTP ${response.status}`)
  return data
}
function saveBlob(blob, filename) { const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url) }

export default function DatabaseControlPlaneEnhanced() {
  const [service, setService] = useState('social/blog'), [tables, setTables] = useState([]), [table, setTable] = useState('')
  const [rows, setRows] = useState([]), [analysis, setAnalysis] = useState(null), [query, setQuery] = useState('')
  const [mode, setMode] = useState('add'), [file, setFile] = useState(null), [preview, setPreview] = useState(null)
  const [busy, setBusy] = useState(false), [message, setMessage] = useState('')
  const current = useMemo(() => SERVICES.find(x => x[0] === service) || SERVICES[0], [service])
  const blog = service === 'social/blog', payment = service === 'payment-service'

  useEffect(() => { setTables([]); setTable(''); setRows([]); setAnalysis(null); setFile(null); setPreview(null); setMessage(''); if (service === 'social/blog') inspectBlog(); if (service === 'payment-service') inspectPayment() }, [service])

  async function inspectPayment() {
    setBusy(true); setMessage('')
    try { const data = await api('/api/v1/admin/tables'); setTables(Array.isArray(data) ? data : []); if (data?.[0]?.name) inspectPaymentTable(data[0].name) }
    catch (e) { setMessage(`Database inspection failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function inspectPaymentTable(name = table) {
    if (!name) return; setBusy(true); setMessage(''); setTable(name)
    try { const suffix = query ? `?limit=${PAGE_SIZE}&offset=0&search=${encodeURIComponent(query)}` : `?limit=${PAGE_SIZE}&offset=0`; const data = await api(`/api/v1/admin/tables/${encodeURIComponent(name)}${suffix}`); setRows(data?.rows || []); setAnalysis(await api(`/api/v1/admin/tables/${encodeURIComponent(name)}/analysis`)) }
    catch (e) { setMessage(`Entity inspection failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function inspectBlog() {
    setBusy(true); setMessage('')
    try { const [a, r] = await Promise.all([api('/api/v1/admin/blog-data/analysis'), api('/api/v2/blog/admin')]); setAnalysis(a); setRows(Array.isArray(r) ? r : (r?.items || [])) }
    catch (e) { setMessage(`Blog inspection failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function exportData(format) {
    if (!blog && !table) return; setBusy(true); setMessage('')
    try { const path = blog ? `/api/v1/admin/blog-data/export?format=${format}` : `/api/v1/admin/tables/${encodeURIComponent(table)}/export?format=${format}`; const response = await fetch(path, { headers: authHeaders() }); if (!response.ok) throw new Error(`HTTP ${response.status}`); saveBlob(await response.blob(), `${blog ? 'blog_posts' : table}.${format}`) }
    catch (e) { setMessage(`Export failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function previewImport(event) {
    const selected = event.target.files?.[0]; setFile(selected || null); setPreview(null); if (!selected || !blog) return; setBusy(true); setMessage('')
    try { const form = new FormData(); form.append('file', selected); setPreview(await api(`/api/v1/admin/blog-data/import/preview?operation=${encodeURIComponent(mode)}`, { method: 'POST', body: form })) }
    catch (e) { setMessage(`Import validation failed: ${e.message}`) } finally { setBusy(false) }
  }
  async function commitImport() {
    if (!file || !preview || !blog) return; const destructive = mode === 'delete' || mode === 'replace_rows'; if (destructive && !window.confirm(`Confirm ${mode.replace('_', ' ')} for the current tenant?`)) return; setBusy(true); setMessage('')
    try { const form = new FormData(); form.append('file', file); const suffix = destructive ? '&confirm=true' : ''; const result = await api(`/api/v1/admin/blog-data/import?operation=${encodeURIComponent(mode)}${suffix}`, { method: 'POST', body: form }); setMessage(`Import committed: ${JSON.stringify(result)}`); setFile(null); setPreview(null); inspectBlog() }
    catch (e) { setMessage(`Import failed and was rolled back: ${e.message}`) } finally { setBusy(false) }
  }

  return <main style={styles.page}><div style={styles.wrap}><header><div style={styles.title}><Database size={26}/><h1>Database Control Plane</h1></div><p style={styles.muted}>Browser operations stay on the Shopnoltd API origin; protected stores remain controlled by their owning services.</p></header>
    <div style={styles.metrics}><Metric icon={<Database size={17}/>} label="Data domains" value={SERVICES.length}/><Metric icon={<ShieldCheck size={17}/>} label="Protected boundaries" value={SERVICES.filter(x => x[2] !== 'crud').length}/><Metric icon={<Lock size={17}/>} label="Generic financial writes" value="0"/><Metric icon={<BarChart3 size={17}/>} label="HD / 4K" value="Responsive"/></div>
    {message && <div style={styles.notice}>{message}</div>}
    <div style={styles.layout}><aside style={styles.panel}><strong>Services / stores</strong>{SERVICES.map(x => <button key={x[0]} onClick={() => setService(x[0])} style={{...styles.nav, ...(service === x[0] ? styles.active : {})}}>{x[0]}<small>{x[1]} · {x[2]}</small></button>)}</aside>
      <section style={{display:'grid',gap:14}}><section style={styles.panel}><div style={styles.between}><div><h2 style={{margin:0}}>{current[0]}</h2><div style={styles.muted}>{current[1]}</div></div><span style={styles.badge}>{current[2]}</span></div></section>
      {blog && <section style={styles.panel}><div style={styles.between}><div><h3 style={{margin:0}}>Blog data operations</h3><p style={styles.muted}>Inspect, analyze, import/export and guarded tenant-scoped operations.</p></div><button onClick={inspectBlog} disabled={busy} style={styles.action}><RefreshCw size={13}/> Inspect</button></div><div style={styles.row}>{['json','csv','xlsx','pdf'].map(f=><button key={f} onClick={()=>exportData(f)} style={styles.small}><Download size={13}/> {f.toUpperCase()}</button>)}<label style={styles.small}><FileUp size={13}/> Import<input type="file" accept=".csv,.json,.xlsx" onChange={previewImport} hidden/></label></div><div style={styles.row}>{MODES.map(([v,l])=><button key={v} onClick={()=>setMode(v)} style={{...styles.small,...(mode===v?styles.selected:{})}}>{l}</button>)}</div>{mode==='create_table'&&<div style={styles.notice}>BlogPost schema is service-owned; arbitrary schema replacement is denied.</div>}{preview&&<pre style={styles.pre}>{JSON.stringify(preview,null,2)}</pre>}{file&&<div style={styles.between}><span>{file.name}</span><button onClick={commitImport} disabled={!preview||busy} style={styles.action}>Commit transaction</button></div>}</section>}
      {payment && <section style={styles.panel}><div style={styles.between}><div><h3 style={{margin:0}}>Protected payment database</h3><p style={styles.muted}>Inspection, search, analysis and exports are available; generic money-moving writes remain disabled.</p></div><button onClick={inspectPayment} disabled={busy} style={styles.action}><RefreshCw size={13}/> Inspect</button></div>{tables.length>0&&<div style={styles.scroll}><table style={styles.table}><thead><tr><th>Entity</th><th>Write</th><th>Columns</th><th>Sensitive</th></tr></thead><tbody>{tables.map(x=><tr key={x.name} onClick={()=>inspectPaymentTable(x.name)}><td>{x.name}</td><td>{x.writable?'Controlled':'No'}</td><td>{x.columns?.length??'—'}</td><td>{x.financially_sensitive?'Protected':'Policy'}</td></tr>)}</tbody></table></div>}{table&&<div style={styles.row}><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search all columns…" style={styles.input}/><button onClick={()=>inspectPaymentTable()} style={styles.action}>Search</button>{['json','csv','xlsx'].map(f=><button key={f} onClick={()=>exportData(f)} style={styles.small}><Download size={13}/> {f.toUpperCase()}</button>)}</div>}</section>}
      {!blog&&!payment&&<section style={styles.panel}><h3 style={{marginTop:0}}>Service-owned adapter</h3><p style={styles.muted}>This domain is not exposed as arbitrary database CRUD. Use its validated application/service workflow.</p></section>}
      {analysis&&<section style={styles.panel}><h3 style={{marginTop:0}}>Analysis</h3><pre style={styles.pre}>{JSON.stringify(analysis,null,2)}</pre></section>}
      {rows.length>0&&<section style={styles.panel}><h3 style={{marginTop:0}}>Entity preview</h3><div style={styles.scroll}><table style={styles.table}><thead><tr>{Object.keys(rows[0]).slice(0,8).map(k=><th key={k}>{k}</th>)}</tr></thead><tbody>{rows.slice(0,20).map((r,i)=><tr key={r.id??i}>{Object.keys(rows[0]).slice(0,8).map(k=><td key={k}>{String(r[k]??'')}</td>)}</tr>)}</tbody></table></div></section>}</section></div></div></main>
}
function Metric({icon,label,value}){return <div style={styles.metric}><div>{icon}</div><small>{label}</small><strong>{value}</strong></div>}
const styles={page:{minHeight:'calc(100vh - 64px)',background:'#0f1419',color:'#e6edf3',padding:'clamp(14px,3vw,36px)'},wrap:{maxWidth:1600,margin:'0 auto'},title:{display:'flex',alignItems:'center',gap:10},muted:{color:'#9da7b3',marginTop:6},metrics:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:10,marginBottom:14},metric:{background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:14,display:'grid',gap:5},layout:{display:'grid',gridTemplateColumns:'minmax(220px,300px) minmax(0,1fr)',gap:14},panel:{background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:16},between:{display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'},nav:{display:'block',width:'100%',textAlign:'left',padding:'9px 10px',marginTop:5,border:0,borderRadius:7,background:'transparent',color:'#d8dee6',cursor:'pointer'},active:{background:'#243244'},badge:{padding:'5px 8px',borderRadius:999,border:'1px solid #3a4655',fontSize:12},action:{display:'inline-flex',alignItems:'center',gap:6,padding:'8px 11px',borderRadius:7,border:'1px solid #3a4655',background:'#1e2935',color:'#fff',cursor:'pointer'},small:{display:'inline-flex',alignItems:'center',gap:6,padding:'6px 9px',borderRadius:7,border:'1px solid #3a4655',background:'#1e2935',color:'#fff',cursor:'pointer',fontSize:12},selected:{borderColor:'#d4a054',background:'#2b251a'},row:{display:'flex',flexWrap:'wrap',gap:7,marginTop:12},notice:{padding:10,margin:'10px 0',border:'1px solid #5b4726',background:'#201b13',borderRadius:7,color:'#e5c78d',overflowWrap:'anywhere'},pre:{maxHeight:300,overflow:'auto',background:'#0b0f14',padding:10,borderRadius:7,fontSize:12},input:{flex:1,minWidth:180,padding:9,borderRadius:7,border:'1px solid #3a4655',background:'#0b0f14',color:'#fff'},scroll:{overflowX:'auto',marginTop:12},table:{width:'100%',borderCollapse:'collapse',fontSize:13}}
