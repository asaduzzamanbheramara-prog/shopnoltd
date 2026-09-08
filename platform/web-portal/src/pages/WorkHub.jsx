import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const box = { maxWidth: 1100, margin: '0 auto', padding: '28px 16px 80px', fontFamily: 'system-ui, sans-serif' }
const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14 }
const input = { width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }

function Browse() {
  const [works, setWorks] = useState([])
  const [loading, setLoading] = useState(true)
  const load = () => platformApi.works('open').then(setWorks).catch(e => alert(e.message)).finally(() => setLoading(false))
  useEffect(load, [])
  async function accept(id) { try { await platformApi.acceptWork(id); load() } catch (e) { alert(e.message) } }
  return <>
    <h1>Work</h1><p style={{ color: '#64748b' }}>Browse open tasks, accept one, complete it and submit proof.</p>
    {loading && <p>Loading…</p>}
    {works.map(w => <article key={w.id} style={card}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}><h3 style={{ marginTop: 0 }}>{w.title}</h3><b>{w.reward_amount} {w.currency}</b></div>
      <p>{w.description}</p>{w.requirements && <p><b>Requirements:</b> {w.requirements}</p>}
      <small>Slots: {w.max_workers} · Deadline: {w.deadline ? new Date(w.deadline).toLocaleString() : 'No deadline'}</small>
      <div style={{ marginTop: 12 }}><button onClick={() => accept(w.id)}>Accept work</button></div>
    </article>)}
    {!loading && works.length === 0 && <div style={card}>No open work is available.</div>}
  </>
}

function Create() {
  const [form, setForm] = useState({ title: '', description: '', requirements: '', reward_amount: '', currency: 'BDT', max_workers: 1, deadline: '' })
  const [done, setDone] = useState('')
  const update = e => setForm({ ...form, [e.target.name]: e.target.value })
  async function submit(e) { e.preventDefault(); try { const w = await platformApi.createWork(form); setDone(`Created work ${w.id}. Reward funding/settlement is intentionally not moved by this marketplace layer yet.`); setForm({ title: '', description: '', requirements: '', reward_amount: '', currency: 'BDT', max_workers: 1, deadline: '' }) } catch (e) { alert(e.message) } }
  return <><h1>Create Work</h1><p style={{ color: '#64748b' }}>Publish a paid-work specification. Financial settlement remains separate from task state.</p><form onSubmit={submit} style={card}>
    <label>Title<input name="title" value={form.title} onChange={update} style={input} required /></label>
    <label>Description<textarea name="description" value={form.description} onChange={update} style={{ ...input, marginTop: 6 }} rows={5} required /></label>
    <label>Requirements<textarea name="requirements" value={form.requirements} onChange={update} style={{ ...input, marginTop: 6 }} rows={3} /></label>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))', gap: 10 }}>
      <label>Reward<input type="number" min="0.00000001" step="any" name="reward_amount" value={form.reward_amount} onChange={update} style={input} required /></label>
      <label>Currency<input name="currency" value={form.currency} onChange={update} style={input} /></label>
      <label>Max workers<input type="number" min="1" max="1000" name="max_workers" value={form.max_workers} onChange={update} style={input} /></label>
      <label>Deadline<input type="datetime-local" name="deadline" value={form.deadline} onChange={update} style={input} /></label>
    </div>
    <button type="submit" style={{ marginTop: 12 }}>Create work</button>{done && <p>{done}</p>}
  </form></>
}

function Active() {
  const [items, setItems] = useState([])
  useEffect(() => { platformApi.activeWorks().then(setItems).catch(e => alert(e.message)) }, [])
  const [proof, setProof] = useState({})
  async function submit(id) { try { await platformApi.submitWork(id, proof[id] || ''); alert('Submission sent'); setProof({ ...proof, [id]: '' }) } catch (e) { alert(e.message) } }
  return <><h1>My Active Works</h1>{items.map(x => <article key={x.assignment_id} style={card}><h3>{x.work.title}</h3><p>{x.work.description}</p><textarea rows={4} value={proof[x.work.id] || ''} onChange={e => setProof({ ...proof, [x.work.id]: e.target.value })} placeholder="Evidence, result URL, notes, or proof" style={input} /><button onClick={() => submit(x.work.id)} style={{ marginTop: 8 }}>Submit result</button></article>)}{items.length === 0 && <div style={card}>You have no active work.</div>}</>
}

function Submissions() {
  const [items, setItems] = useState([])
  useEffect(() => { platformApi.submissions().then(setItems).catch(e => alert(e.message)) }, [])
  return <><h1>My Submission</h1>{items.map(x => <article key={x.id} style={card}><b>{x.status.toUpperCase()}</b><p>Work: {x.work_id}</p><p>{x.proof}</p>{x.review_note && <p>Review: {x.review_note}</p>}</article>)}{items.length === 0 && <div style={card}>No submissions yet.</div>}</>
}

export default function WorkHub() {
  const path = useLocation().pathname
  return <main style={box}><nav style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 20 }}><Link to="/work">Work</Link><Link to="/create-work">Create Work</Link><Link to="/my-active-work">My Active Works</Link><Link to="/my-submission">My Submission</Link></nav>{path === '/create-work' ? <Create /> : path === '/my-active-work' ? <Active /> : path === '/my-submission' ? <Submissions /> : <Browse />}</main>
}
