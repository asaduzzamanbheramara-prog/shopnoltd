import { useEffect, useState } from 'react'
import { ArrowLeft, CheckCircle2, Github, Plus, RefreshCw, Server, Trash2, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'
import { authenticatedRequest } from '../lib/financialApi'

const API='/api/v1/connections'
async function request(path, options={}) { return authenticatedRequest(API+path, options) }

const button={border:'1px solid #d1d5db',borderRadius:8,padding:'8px 11px',background:'#fff',cursor:'pointer'}
const input={width:'100%',boxSizing:'border-box',padding:9,border:'1px solid #d1d5db',borderRadius:8}

export default function AIConnections(){
 const [items,setItems]=useState([]),[kind,setKind]=useState('github'),[name,setName]=useState(''),[url,setUrl]=useState(''),[secret,setSecret]=useState(''),[busy,setBusy]=useState(false),[error,setError]=useState(''),[results,setResults]=useState({})
 const load=async()=>{try{setItems(await request(''))}catch(e){setError(e.message)}}
 useEffect(()=>{load()},[])
 const add=async e=>{e.preventDefault();setBusy(true);setError('')
  try{const x=await request('',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,name,base_url:kind==='local'?url:null,secret:secret||null,config:{}})});setItems(v=>[...v,x]);setName('');setUrl('');setSecret('')}
  catch(e){setError(e.message)}finally{setBusy(false)}
 }
 const test=async id=>{const x=await request('/'+id+'/test',{method:'POST'});setResults(v=>({...v,[id]:x}))}
 const remove=async id=>{if(!confirm('Delete this connection?'))return;await request('/'+id,{method:'DELETE'});load()}
 const repos=async id=>{try{const x=await request('/'+id+'/github/repos');setResults(v=>({...v,[id]:{repos:x}}))}catch(e){setResults(v=>({...v,[id]:{error:e.message}}))}}
 return <main style={{maxWidth:1050,margin:'0 auto',padding:24}}>
  <Link to="/ai" style={{display:'inline-flex',gap:6,alignItems:'center',color:'#374151',textDecoration:'none',marginBottom:18}}><ArrowLeft size={16}/> Back to AI</Link>
  <h1 style={{margin:'0 0 6px'}}>AI Connections</h1>
  <p style={{margin:'0 0 22px',color:'#6b7280'}}>Connect GitHub repositories or an OpenAI-compatible local AI server. Secrets are encrypted server-side.</p>
  {error&&<div style={{padding:10,background:'#fef2f2',color:'#991b1b',borderRadius:8,marginBottom:14}}>{error}</div>}
  <form onSubmit={add} style={{border:'1px solid #e5e7eb',borderRadius:12,padding:18,marginBottom:24,display:'grid',gap:10}}>
   <h2 style={{margin:0,fontSize:18}}>Add connection</h2>
   <select value={kind} onChange={e=>setKind(e.target.value)} style={input}><option value="github">GitHub</option><option value="local">Local / OpenAI-compatible server</option></select>
   <input required value={name} onChange={e=>setName(e.target.value)} placeholder="Connection name" style={input}/>
   {kind==='local'&&<input required value={url} onChange={e=>setUrl(e.target.value)} placeholder="http://localhost:11434/v1" style={input}/>}
   <input required={kind==='github'} type="password" value={secret} onChange={e=>setSecret(e.target.value)} placeholder={kind==='github'?'GitHub access token':'Optional bearer/API key'} style={input}/>
   <button disabled={busy} style={{...button,background:'#111827',color:'#fff',borderColor:'#111827'}}><Plus size={15}/>{busy?'Saving…':'Add connection'}</button>
  </form>
  <div style={{display:'grid',gap:12}}>
   {items.map(x=><section key={x.id} style={{border:'1px solid #e5e7eb',borderRadius:12,padding:16}}>
    <div style={{display:'flex',justifyContent:'space-between',gap:10}}>
     <div style={{display:'flex',gap:8,alignItems:'center',fontWeight:700}}>{x.kind==='github'?<Github size={18}/>:<Server size={18}/>} {x.name}</div>
     <button onClick={()=>remove(x.id)} style={{...button,color:'#991b1b'}}><Trash2 size={15}/></button>
    </div>
    <div style={{fontSize:12,color:'#6b7280',marginTop:5}}>{x.base_url||'GitHub API'} · {x.secret_masked||'No credential'}</div>
    <div style={{display:'flex',gap:8,flexWrap:'wrap',marginTop:12}}>
      <button onClick={()=>test(x.id)} style={button}><Zap size={14}/> Test</button>
      {x.kind==='github'&&<button onClick={()=>repos(x.id)} style={button}><RefreshCw size={14}/> Load repositories</button>}
    </div>
    {results[x.id]?.message&&<div style={{marginTop:10,padding:9,borderRadius:8,background:results[x.id].ok?'#f0fdf4':'#fef2f2'}}><CheckCircle2 size={14}/> {results[x.id].message}</div>}
    {results[x.id]?.repos&&<div style={{marginTop:10,display:'grid',gap:5}}>{results[x.id].repos.map(r=><div key={r.full_name} style={{padding:8,border:'1px solid #eee',borderRadius:7}}>{r.full_name} · {r.default_branch}</div>)}</div>}
    {results[x.id]?.error&&<div style={{marginTop:10,color:'#991b1b'}}>{results[x.id].error}</div>}
   </section>)}
   {!items.length&&<div style={{padding:25,border:'1px dashed #d1d5db',borderRadius:10,color:'#6b7280'}}>No connections yet.</div>}
  </div>
 </main>
}
