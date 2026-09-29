import { useEffect, useState } from 'react'
import { RefreshCw, Save, Trash2, Globe2 } from 'lucide-react'
import AdminRoute from '../components/AdminRoute'

const TASK_TYPES = [
  ['simple','Simple Task'],['job','Job / Work'],['follow','Follow'],['like','Like'],['comment','Comment'],
  ['share','Share'],['view','View'],['visit','Visit'],['review','Review'],['social','Social Action'],
  ['data','Data Task'],['upload','Upload'],['custom','Custom'],['watch','Watch']
]

async function api(path, options = {}) {
  const token = localStorage.getItem('shopno_token')
  const headers = { Accept:'application/json', ...(token ? { Authorization:`Bearer ${token}` } : {}), ...(options.body ? {'Content-Type':'application/json'} : {}), ...(options.headers||{}) }
  const r = await fetch(path, {...options, headers})
  const text = await r.text()
  let data
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!r.ok) throw new Error(data?.detail || data?.message || text || `HTTP ${r.status}`)
  return data
}

function Editor({ taskType, currency, current, onSaved }) {
  const [rate,setRate] = useState(current?.rate || '')
  const [enabled,setEnabled] = useState(current?.enabled !== false)
  const [busy,setBusy] = useState(false)
  useEffect(()=>{setRate(current?.rate || '');setEnabled(current?.enabled !== false)},[current])
  async function save(){
    setBusy(true)
    try {
      await api(`/api/v3/work/admin/rates/${encodeURIComponent(taskType)}/${encodeURIComponent(currency)}`,{method:'PUT',body:JSON.stringify({rate,enabled})})
      await onSaved()
    } catch(e){ alert(e.message) } finally { setBusy(false) }
  }
  async function remove(){
    if(!current || !window.confirm(`Remove ${taskType} rate in ${currency}?`)) return
    setBusy(true)
    try { await api(`/api/v3/work/admin/rates/${encodeURIComponent(taskType)}/${encodeURIComponent(currency)}`,{method:'DELETE'}); await onSaved() }
    catch(e){ alert(e.message) } finally { setBusy(false) }
  }
  return <div style={{display:'grid',gridTemplateColumns:'minmax(150px,1fr) 120px 150px auto auto',gap:8,alignItems:'center',padding:'10px 0',borderBottom:'1px solid #e5e7eb'}}>
    <strong>{TASK_TYPES.find(x=>x[0]===taskType)?.[1] || taskType}</strong>
    <span>{currency}</span>
    <input type="number" min="0" step="any" value={rate} onChange={e=>setRate(e.target.value)} placeholder="Rate" style={input}/>
    <label style={{display:'flex',gap:6,alignItems:'center'}}><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/> Enabled</label>
    <div style={{display:'flex',gap:6}}><button disabled={busy} onClick={save}><Save size={15}/> Save</button>{current&&<button disabled={busy} onClick={remove}><Trash2 size={15}/> Remove</button>}</div>
  </div>
}

function RatesPage(){
  const [data,setData]=useState({supported_currencies:[],rates:{}})
  const [currency,setCurrency]=useState('USD')
  const [taskType,setTaskType]=useState('simple')
  const [busy,setBusy]=useState(false)
  const [showAll,setShowAll]=useState(false)
  async function load(){
    setBusy(true)
    try {
      const d=await api('/api/v3/work/admin/rates')
      setData(d)
      if(d.supported_currencies?.length && !d.supported_currencies.includes(currency)) setCurrency(d.supported_currencies[0])
    } catch(e){alert(e.message)} finally{setBusy(false)}
  }
  useEffect(()=>{load()},[])
  const rows=TASK_TYPES.filter(([t])=>showAll || (data.rates?.[t]||[]).some(r=>r.currency===currency)).map(([t])=>({taskType:t,current:(data.rates?.[t]||[]).find(r=>r.currency===currency)}))
  return <AdminRoute><main style={{maxWidth:1100,margin:'0 auto',padding:'24px 16px'}}>
    <header style={{display:'flex',justifyContent:'space-between',gap:12,alignItems:'center',flexWrap:'wrap'}}>
      <div><h1 style={{marginBottom:6}}>Global Task Rates</h1><p style={{color:'#64748b'}}>Configure per-completion earning rates independently for every supported currency. No country is assumed.</p></div>
      <button onClick={load} disabled={busy}><RefreshCw size={16}/> Refresh</button>
    </header>
    <section style={card}><div style={{display:'flex',gap:10,alignItems:'center',flexWrap:'wrap'}}><Globe2 size={20}/><label>Currency <select value={currency} onChange={e=>setCurrency(e.target.value)} style={input}>{data.supported_currencies.map(c=><option key={c}>{c}</option>)}</select></label><label>Task type <select value={taskType} onChange={e=>setTaskType(e.target.value)} style={input}>{TASK_TYPES.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select></label><label style={{display:'flex',gap:6,alignItems:'center'}}><input type="checkbox" checked={showAll} onChange={e=>setShowAll(e.target.checked)}/> Show unconfigured rates</label></div></section>
    <section style={card}><h2 style={{marginTop:0}}>Configured rates — {currency}</h2>{rows.length ? rows.map(r=><Editor key={r.taskType} taskType={r.taskType} currency={currency} current={r.current} onSaved={load}/>) : <p style={{color:'#64748b'}}>No rates configured for this currency yet. Select “Show unconfigured rates” to add them.</p>}</section>
    <section style={card}><h2 style={{marginTop:0}}>Global currency model</h2><p>Task earnings retain their configured amount and currency through completion and settlement. Currency conversion is not silently applied to worker earnings; use the existing Shopnoltd exchange/payment flow when conversion is required.</p><p style={{color:'#64748b'}}>The same currency registry used by the marketplace API is used here, so adding or changing supported currencies does not require a second Bangladesh-specific list.</p></section>
  </main></AdminRoute>
}
const card={background:'#fff',border:'1px solid #e2e8f0',borderRadius:14,padding:18,marginTop:16,boxShadow:'0 2px 8px rgba(15,23,42,.05)'}
const input={padding:'8px 10px',border:'1px solid #cbd5e1',borderRadius:8}
export default RatesPage
