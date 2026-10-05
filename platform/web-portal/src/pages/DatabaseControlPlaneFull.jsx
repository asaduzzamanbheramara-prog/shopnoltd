import { useEffect, useMemo, useState } from 'react'
import { tryRefresh } from '../lib/tokenRefresh'
import { Database, Download, Edit3, Plus, RefreshCw, Save, Search, ShieldCheck, Trash2, X } from 'lucide-react'

const PAGE = 50
const apiHeaders = () => {
  const token = localStorage.getItem('shopno_token')
  return { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) }
}
async function api(path, options = {}) {
  let token = localStorage.getItem('shopno_token')
  let response
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const headers = { ...apiHeaders(), ...(options.headers || {}) }
    if (token) headers.Authorization = `Bearer ${token}`
    response = await fetch(path, { ...options, headers })
    if (response.status !== 401 || attempt === 1) break
    const refreshed = await tryRefresh()
    if (!refreshed) break
    token = refreshed
  }
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || text || `HTTP ${response.status}`)
  return data
}
function csv(rows, columns) {
  const esc = value => {
    const text = value == null ? '' : typeof value === 'object' ? JSON.stringify(value) : String(value)
    return /[",\n]/.test(text) ? '"' + text.replace(/"/g, '""') + '"' : text
  }
  return [columns.map(c => esc(c.name)).join(','), ...rows.map(row => columns.map(c => esc(row[c.name])).join(','))].join('\n')
}
function download(text, filename, type = 'text/plain') {
  const blob = new Blob([text], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
function inputValue(column, value) {
  if (value == null) return ''
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
function coerce(column, value) {
  if (value === '' && column.is_nullable === 'YES') return null
  const type = String(column.data_type || '').toLowerCase()
  if (/integer|numeric|decimal|real|double/.test(type)) return Number(value)
  if (type === 'boolean') return value === true || value === 'true'
  if (/json/.test(type)) { try { return JSON.parse(value) } catch { throw new Error(`${column.column_name} must contain valid JSON`) } }
  return value
}

export default function DatabaseControlPlaneFull() {
  const [declared, setDeclared] = useState([])
  const [live, setLive] = useState([])
  const [database, setDatabase] = useState('')
  const [schema, setSchema] = useState('public')
  const [table, setTable] = useState('')
  const [data, setData] = useState(null)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const [editor, setEditor] = useState(null)
  const [importPreview, setImportPreview] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [analysis, setAnalysis] = useState(null)

  async function refresh() {
    setBusy(true); setError('')
    try {
      const [catalog, inventory] = await Promise.all([
        api('/api/v1/admin/database/catalog'),
        api('/api/v1/admin/database/live-catalog'),
      ])
      setDeclared(catalog?.databases || [])
      setLive(inventory?.databases || [])
      const first = inventory?.databases?.find(x => x.classification === 'application')?.database || catalog?.databases?.[0]?.database || ''
      setDatabase(current => current || first)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { refresh() }, [])

  const db = useMemo(() => live.find(x => x.database === database), [live, database])
  const schemas = db?.schemas || ['public']
  const tables = db?.tables?.filter(t => !schema || t.schema === schema) || []
  const selected = tables.find(t => t.name === table) || tables[0]
  const capability = selected?.capability || { readable: false, writable: false, destructive: false, importable: false, exportable: false, protected_reason: 'No explicit capability' }
  const declaredServices = db?.declared_services || declared.filter(x => x.database === database).map(x => x.service)
  const appDatabases = live

  useEffect(() => {
    if (db && !schemas.includes(schema)) setSchema(schemas[0] || 'public')
  }, [db, schema, schemas])
  useEffect(() => {
    if (selected?.name && selected.name !== table) { setTable(selected.name); setOffset(0) }
  }, [selected, table])

  async function inspect(nextOffset = offset) {
    if (!selected?.name || !capability.readable) return
    setBusy(true); setError('')
    try {
      const q = new URLSearchParams({ limit: String(PAGE), offset: String(nextOffset) })
      if (search) q.set('q', search)
      const result = await api(`/api/v1/admin/database/tables/${encodeURIComponent(database)}/${encodeURIComponent(selected.schema)}/${encodeURIComponent(selected.name)}/rows?${q}`)
      setData(result)
      setOffset(nextOffset)
      const meta = await api(`/api/v1/admin/database/tables/${encodeURIComponent(database)}/${encodeURIComponent(selected.schema)}/${encodeURIComponent(selected.name)}/analysis`)
      setAnalysis(meta)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  useEffect(() => { if (selected?.name) inspect(0) }, [database, schema, table])

  function startAdd() {
    const values = {}
    ;(data?.columns || []).forEach(column => { if (!column.column_name || column.column_name === 'id') return; values[column.column_name] = '' })
    setEditor({ mode: 'add', values })
  }
  function startEdit(row) { setEditor({ mode: 'edit', key: row, values: Object.fromEntries((data?.columns || []).map(c => [c.column_name, inputValue(c, row[c.column_name])])) }) }
  async function save() {
    if (!editor) return
    setBusy(true); setError('')
    try {
      const values = {}
      ;(data?.columns || []).forEach(column => {
        if (!(column.column_name in editor.values)) return
        values[column.column_name] = coerce(column, editor.values[column.column_name])
      })
      const base = `/api/v1/admin/database/tables/${encodeURIComponent(database)}/${encodeURIComponent(selected.schema)}/${encodeURIComponent(selected.name)}/rows`
      if (editor.mode === 'add') await api(base, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(values) })
      else await api(base, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key: editor.key, values }) })
      setEditor(null); setMessage(editor.mode === 'add' ? 'Row created.' : 'Row updated.'); await inspect(offset)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function remove(row) {
    if (!capability.destructive) return
    if (!window.confirm('Delete this database row? This action is permanent and audited where the service audit stream is available.')) return
    setBusy(true); setError('')
    try {
      const keyColumns = (data?.columns || []).filter(c => c.primary_key)
      if (!keyColumns.length) throw new Error('Delete requires a declared primary key.')
      const key = Object.fromEntries(keyColumns.map(c => [c.column_name, row[c.column_name]]))
      const base = `/api/v1/admin/database/tables/${encodeURIComponent(database)}/${encodeURIComponent(selected.schema)}/${encodeURIComponent(selected.name)}/rows`
      await api(base, { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ key }) })
      setMessage('Row deleted.'); await inspect(offset)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }
  async function chooseImport(event) {
    const file = event.target.files?.[0]
    setImportPreview(null)
    if (!file || !capability.importable || !capability.writable) return
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      const rows = Array.isArray(parsed) ? parsed : parsed.rows
      if (!Array.isArray(rows) || !rows.length || rows.length > 5000) throw new Error('Import must be a JSON array (or {rows:[...]}) containing 1-5000 rows.')
      setImportPreview({ file, rows })
    } catch (e) { setError(e.message) }
  }
  async function commitImport() {
    if (!importPreview) return
    if (!window.confirm(`Import ${importPreview.rows.length} rows into ${selected.name}? The transaction will roll back if validation or insertion fails.`)) return
    setBusy(true); setError('')
    try {
      await api(`/api/v1/admin/database/tables/${encodeURIComponent(database)}/${encodeURIComponent(selected.schema)}/${encodeURIComponent(selected.name)}/import`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ rows: importPreview.rows }) })
      setImportPreview(null); setMessage('Import committed transactionally.'); await inspect(0)
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  function exportCurrent(format) {
    if (!selected) return
    if (format === 'csv' && data?.rows) download(csv(data.rows, data.columns || []), `${database}-${selected.name}.csv`, 'text/csv')
    else download(JSON.stringify(data?.rows || [], null, 2), `${database}-${selected.name}.json`, 'application/json')
  }

  return <main style={styles.page}><div style={styles.wrap}>
    <header style={styles.header}><div><div style={styles.title}><Database size={25}/><h1>Website Database Management</h1></div><p style={styles.muted}>Complete live database/table inventory with capability-gated management. Safe tables expose CRUD/import/export; identity, financial, security and ledger data uses validated service administration rather than unsafe generic mutation. No browser SQL.</p></div><button style={styles.button} onClick={refresh} disabled={busy}><RefreshCw size={15}/> Refresh</button></header>
    {error && <div style={styles.error}>{error}</div>}{message && <div style={styles.message}>{message}<button onClick={() => setMessage('')} style={styles.icon}><X size={14}/></button></div>}
    <section style={styles.metrics}><Metric icon={<Database/>} label="Live databases" value={appDatabases.length}/><Metric icon={<ShieldCheck/>} label="Declared services" value={declared.length}/><Metric icon={<ShieldCheck/>} label="Protected tables" value={live.reduce((n,d)=>n+(d.tables||[]).filter(t=>t.capability?.protected_reason).length,0)}/><Metric icon={<Database/>} label="Current database" value={database || '—'}/></section>
    <section style={styles.toolbar}>
      <label>Database<select value={database} onChange={e=>{setDatabase(e.target.value);setTable('');setOffset(0)}}>{appDatabases.map(d=><option key={d.database} value={d.database}>{d.database}{d.declared_services?.length?' · '+d.declared_services.join(', '):''}</option>)}</select></label>
      <label>Schema<select value={schema} onChange={e=>{setSchema(e.target.value);setTable('');setOffset(0)}}>{schemas.map(s=><option key={s} value={s}>{s}</option>)}</select></label>
      <label>Table<select value={selected?.name || ''} onChange={e=>{setTable(e.target.value);setOffset(0)}}>{tables.map(t=><option key={t.name} value={t.name}>{t.name}{t.capability?.writable?' · writable':' · protected'}</option>)}</select></label>
      <label style={styles.search}><Search size={15}/><input value={search} onChange={e=>setSearch(e.target.value)} onKeyDown={e=>e.key==='Enter'&&inspect(0)} placeholder="Search current table"/></label><button style={styles.button} onClick={()=>inspect(0)} disabled={busy}><Search size={15}/> Search</button>
    </section>
    {db && <section style={styles.panel}><div style={styles.between}><div><strong>{declaredServices.join(' · ') || 'Live / undeclared database'}</strong><div style={styles.muted}>{database} · {selected?.schema || schema}.{selected?.name || '—'}</div></div><span style={styles.badge}>{capability.writable?'Controlled write':'Protected / read-only'}</span></div>
      {selected && <>
        <div style={styles.capability}><span>Read: {capability.readable?'Yes':'No'}</span><span>Write: {capability.writable?'Yes':'No'}</span><span>Delete: {capability.destructive?'Yes':'No'}</span><span>Import: {capability.importable?'Yes':'No'}</span><span>Export: {capability.exportable?'Yes':'No'}</span><span>{capability.protected_reason || 'Explicitly allowlisted entity'}</span></div>
        {analysis && <div style={styles.analysis}><span>Rows: {analysis.rows}</span><span>Columns: {analysis.columns}</span><span>Primary key: {analysis.primary_key?.join(', ') || 'None'}</span><span>Unique constraints: {analysis.unique_constraints?.length || 0}</span><span>Indexes: {analysis.indexes?.length || 0}</span></div>}
      </>}
      <div style={styles.actions}>{capability.writable && <button style={styles.button} onClick={startAdd}><Plus size={15}/> Add row</button>}{capability.writable && selected && <button style={styles.button} onClick={()=>setEditor(null)}>Clear editor</button>}{capability.exportable && <><button style={styles.button} onClick={()=>exportCurrent('json')}><Download size={15}/> JSON</button><button style={styles.button} onClick={()=>exportCurrent('csv')}><Download size={15}/> CSV</button></>}{selected && capability.readable && <button style={styles.button} onClick={()=>inspect(offset)} disabled={busy}><Search size={15}/> Analyze</button>}{capability.importable && capability.writable && <label style={styles.button}>Import JSON<input type="file" accept="application/json,.json" onChange={chooseImport} style={{display:'none'}} /></label>}</div>
    </section>}
    {importPreview && <section style={styles.panel}><div style={styles.between}><div><h3>Validated import preview</h3><div style={styles.muted}>{importPreview.rows.length} rows ready for transactional import.</div></div><button style={styles.button} onClick={commitImport} disabled={busy}><Save size={15}/> Commit import</button></div><pre style={styles.pre}>{JSON.stringify(importPreview.rows.slice(0,20), null, 2)}</pre></section>}
    {editor && <section style={styles.panel}><div style={styles.between}><h3>{editor.mode==='add'?'Add row':'Edit row'}</h3><button style={styles.icon} onClick={()=>setEditor(null)}><X/></button></div><div style={styles.form}>{(data?.columns||[]).filter(c=>c.column_name!=='id'||editor.mode==='edit').map(column => <label key={column.column_name}>{column.column_name}<small>{column.data_type}{column.primary_key?' · PK':''}{column.is_nullable==='YES'?' · nullable':''}</small><input disabled={editor.mode==='edit'&&column.primary_key} value={editor.values[column.column_name] ?? ''} onChange={e=>setEditor({...editor,values:{...editor.values,[column.column_name]:e.target.value}})} /></label>)}</div><button style={styles.button} onClick={save} disabled={busy}><Save size={15}/> Save</button></section>}
    <section style={styles.panel}><div style={styles.between}><h3>{selected?.name || 'Table'} rows</h3><span className="muted">{data?.offset ?? 0}–{Math.min((data?.offset??0)+(data?.rows?.length||0), (data?.offset??0)+(data?.rows?.length||0))}</span></div><div style={styles.tableWrap}><table><thead><tr>{(data?.columns||[]).map(c=><th key={c.column_name}>{c.column_name}{c.primary_key?' 🔑':''}</th>)}{capability.writable&&<th>Actions</th>}</tr></thead><tbody>{(data?.rows||[]).map((row,i)=><tr key={i}>{(data?.columns||[]).map(c=><td key={c.column_name}>{typeof row[c.column_name]==='object'?JSON.stringify(row[c.column_name]):String(row[c.column_name]??'')}</td>)}{capability.writable&&<td><button style={styles.icon} onClick={()=>startEdit(row)} title="Edit"><Edit3 size={14}/></button>{capability.destructive&&<button style={styles.icon} onClick={()=>remove(row)} title="Delete"><Trash2 size={14}/></button>}</td>}</tr>)}</tbody></table></div><div style={styles.pager}><button style={styles.button} disabled={offset===0||busy} onClick={()=>inspect(Math.max(0,offset-PAGE))}>Previous</button><span>Offset {offset}</span><button style={styles.button} disabled={!data||data.rows.length<PAGE||busy} onClick={()=>inspect(offset+PAGE)}>Next</button></div></section>
  </div></main>
}
function Metric({icon,label,value}){return <div style={styles.metric}>{icon}<small>{label}</small><strong>{value}</strong></div>}
const styles={page:{minHeight:'calc(100vh - 64px)',background:'#0f1419',color:'#e6edf3',padding:'clamp(14px,3vw,36px)'},wrap:{maxWidth:1700,margin:'0 auto'},header:{display:'flex',justifyContent:'space-between',gap:16,alignItems:'flex-start',flexWrap:'wrap'},title:{display:'flex',alignItems:'center',gap:10},muted:{color:'#9da7b3',marginTop:6},metrics:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:10,margin:'14px 0'},metric:{background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:14,display:'grid',gap:5},toolbar:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(180px,1fr))',gap:10,marginBottom:14},toolbarLabel:{display:'grid'},search:{display:'flex',alignItems:'end',gap:6},panel:{background:'#151b22',border:'1px solid #27303b',borderRadius:10,padding:16,marginBottom:14},between:{display:'flex',justifyContent:'space-between',alignItems:'center',gap:10,flexWrap:'wrap'},button:{display:'inline-flex',alignItems:'center',gap:6,padding:'8px 11px',borderRadius:7,border:'1px solid #3a4655',background:'#1e2935',color:'#fff',cursor:'pointer'},icon:{display:'inline-flex',alignItems:'center',justifyContent:'center',padding:6,border:0,background:'transparent',color:'#fff',cursor:'pointer'},badge:{padding:'5px 8px',borderRadius:999,border:'1px solid #3a4655',fontSize:12},capability:{display:'flex',gap:12,flexWrap:'wrap',marginTop:12,color:'#b7c0ca',fontSize:13},analysis:{display:'flex',gap:12,flexWrap:'wrap',marginTop:10,color:'#d7dee7',fontSize:12},actions:{display:'flex',gap:8,flexWrap:'wrap',marginTop:12},form:{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:10,marginBottom:12},tableWrap:{overflow:'auto'},table:{width:'100%',borderCollapse:'collapse',fontSize:13},error:{padding:12,marginBottom:10,border:'1px solid #8b3a3a',background:'#241518',borderRadius:8},message:{position:'relative',padding:12,marginBottom:10,border:'1px solid #3b6b4b',background:'#142017',borderRadius:8},pre:{maxHeight:320,overflow:'auto',background:'#0b0f14',padding:10,borderRadius:7,fontSize:12},pager:{display:'flex',justifyContent:'center',alignItems:'center',gap:10,marginTop:12}}
