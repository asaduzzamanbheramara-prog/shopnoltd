import React, { useCallback, useEffect, useState } from 'react'
import { platformApi } from '../lib/platformApi'

const panel = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 12, padding: 18, boxShadow: '0 1px 2px rgba(15,23,42,.04)' }
const button = { border: 0, borderRadius: 8, padding: '8px 12px', cursor: 'pointer', fontWeight: 600 }
const money = (value, currency) => `${Number(value || 0).toLocaleString(undefined, { maximumFractionDigits: 4 })} ${currency || ''}`

export default function WorkMarketplaceAdmin() {
  const [data, setData] = useState({ summary: {}, items: [] })
  const [submissions, setSubmissions] = useState([])
  const [status, setStatus] = useState('all')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [note, setNote] = useState('')

  const load = useCallback(async () => {
    setError('')
    try {
      const [dashboard, queue] = await Promise.all([platformApi.adminWorks(status), platformApi.adminWorkSubmissions()])
      setData(dashboard || { summary: {}, items: [] })
      setSubmissions(Array.isArray(queue) ? queue : [])
    } catch (e) { setError(e.message || 'Could not load marketplace administration') }
  }, [status])

  useEffect(() => { load() }, [load])

  async function moderate(id, decision) {
    setBusy(`${id}:${decision}`)
    try { await platformApi.moderateWork(id, { decision }); await load() }
    catch (e) { setError(e.message || 'Task moderation failed') }
    finally { setBusy('') }
  }

  async function review(id, decision) {
    const reviewNote = note.trim()
    if (decision === 'rejected' && !reviewNote && !window.confirm('Reject this submission without a note?')) return
    setBusy(`${id}:${decision}`)
    try {
      const item = submissions.find(x => x.id === id)
      let verified = false
      try { verified = !!JSON.parse(item?.proof || '{}').session_id } catch {}
      if (verified) {
        if (decision === 'approved') await platformApi.approveVerifiedSubmission(id)
        else await platformApi.rejectVerifiedSubmission(id, reviewNote || 'Rejected by admin')
      } else {
        await platformApi.reviewSubmission(id, decision, reviewNote)
      }
      setNote(''); await load()
    } catch (e) { setError(e.message || 'Submission review failed') }
    finally { setBusy('') }
  }

  const summary = data.summary || {}
  return <main style={{ maxWidth: 1280, margin: '0 auto', padding: '12px 0 40px', color: '#0f172a' }}>
    <header style={{ display: 'flex', gap: 16, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
      <div><h1 style={{ margin: '0 0 6px' }}>Work Marketplace Control</h1><p style={{ margin: 0, color: '#64748b' }}>Moderate funded tasks, review worker submissions and monitor Shopnoltd task economics.</p></div>
      <button style={{ ...button, background: '#0f172a', color: '#fff' }} onClick={load}>Refresh</button>
    </header>
    {error && <p role="alert" style={{ ...panel, marginTop: 16, borderColor: '#fca5a5', color: '#991b1b' }}>{error}</p>}
    <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 12, margin: '20px 0' }}>
      {[
        ['Tasks', summary.tasks ?? 0], ['Awaiting moderation', summary.pending_review ?? 0], ['Open / full', summary.open ?? 0], ['Pending submissions', summary.pending_submissions ?? 0],
      ].map(([label, value]) => <div key={label} style={panel}><div style={{ color: '#64748b', fontSize: 13 }}>{label}</div><strong style={{ display: 'block', fontSize: 22, marginTop: 6 }}>{value}</strong></div>)}
    </section>
    <p style={{ color: '#64748b', fontSize: 12 }}>{data.budget_note || 'Budget figures are estimates, not realized revenue or confirmed settlement.'}</p>
    <section style={{ ...panel, marginBottom: 16 }}>
      <h2 style={{ margin: '0 0 12px' }}>Budget caps by currency</h2>
      {Object.entries(data.budget_by_currency || {}).map(([currency, amounts]) => <div key={currency} style={{ display: 'flex', gap: 18, flexWrap: 'wrap', padding: '8px 0', borderTop: '1px solid #e2e8f0' }}><b>{currency}</b><span>Gross cap: {money(amounts.gross_budget_estimate, currency)}</span><span>Shopnoltd share cap: {money(amounts.platform_share_estimate, currency)}</span></div>)}
      {!Object.keys(data.budget_by_currency || {}).length && <p style={{ color: '#64748b' }}>No task budgets to summarize.</p>}
    </section>
    <section style={{ ...panel, marginTop: 14 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}><h2 style={{ margin: 0 }}>Task moderation</h2><select value={status} onChange={e => setStatus(e.target.value)} style={{ padding: 8, borderRadius: 8, border: '1px solid #cbd5e1' }}><option value="all">All statuses</option><option value="pending_review">Pending review</option><option value="open">Open</option><option value="paused">Paused</option><option value="closed">Closed</option><option value="rejected">Rejected</option></select></div>
      <div style={{ display: 'grid', gap: 12, marginTop: 16 }}>
        {(data.items || []).map(work => <article key={work.id} style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 14 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}><div><h3 style={{ margin: '0 0 6px' }}>{work.title}</h3><div style={{ color: '#64748b', fontSize: 13 }}>Creator: {work.creator_id} · Status: <b>{work.status}</b> · Type: {work.task_type} / {work.platform}</div></div><div style={{ textAlign: 'right' }}><b>{money(work.reward_amount, work.currency)} / worker</b><div style={{ color: '#64748b', fontSize: 12 }}>Cap: {work.max_workers} workers</div></div></div>
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', marginTop: 10, fontSize: 13 }}><span>Gross budget cap: {money(work.gross_budget_estimate, work.currency)}</span><span>Shopnoltd share cap: {money(work.platform_share_estimate, work.currency)}</span><span>Pending submissions: {work.pending_submissions ?? 0}</span><span>Completed: {work.completed_tasks ?? 0}</span></div>
          {work.description && <p style={{ margin: '10px 0', whiteSpace: 'pre-wrap' }}>{work.description}</p>}
          {work.before_post_screenshot && <div style={{ margin: '10px 0' }}><div style={{ fontSize: 12, color: '#64748b' }}>Creator-provided pre-post evidence</div><img src={work.before_post_screenshot} alt="Creator pre-post evidence" style={{ maxWidth: 320, maxHeight: 180, objectFit: 'contain', borderRadius: 8, border: '1px solid #e2e8f0' }} /></div>}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 10 }}>
            {work.status === 'pending_review' && <><button disabled={!!busy} style={{ ...button, background: '#166534', color: '#fff' }} onClick={() => moderate(work.id, 'approve')}>{busy === `${work.id}:approve` ? 'Approving…' : 'Approve & publish'}</button><button disabled={!!busy} style={{ ...button, background: '#991b1b', color: '#fff' }} onClick={() => moderate(work.id, 'reject')}>{busy === `${work.id}:reject` ? 'Rejecting…' : 'Reject & release budget'}</button></>}
            {['open', 'full'].includes(work.status) && <button disabled={!!busy} style={{ ...button, background: '#b45309', color: '#fff' }} onClick={() => moderate(work.id, 'pause')}>Pause task</button>}
            {work.status === 'paused' && <button disabled={!!busy} style={{ ...button, background: '#0369a1', color: '#fff' }} onClick={() => moderate(work.id, 'resume')}>Resume task</button>}
            {['open', 'full', 'paused'].includes(work.status) && <button disabled={!!busy} style={{ ...button, background: '#475569', color: '#fff' }} onClick={() => moderate(work.id, 'close')}>Close & release unused budget</button>}
          </div>
        </article>)}
        {!data.items?.length && <p style={{ color: '#64748b' }}>No tasks in this view.</p>}
      </div>
    </section>
    <section style={{ ...panel, marginTop: 18 }}>
      <h2 style={{ marginTop: 0 }}>Worker submission review</h2>
      <label style={{ display: 'block', fontSize: 13, color: '#475569', marginBottom: 6 }}>Review note (used for the next decision)</label>
      <input value={note} onChange={e => setNote(e.target.value)} placeholder="Optional approval note or reason for rejection" style={{ width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8, marginBottom: 12 }} />
      <div style={{ display: 'grid', gap: 12 }}>
        {submissions.map(item => <article key={item.id} style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 14 }}><h3 style={{ margin: '0 0 6px' }}>{item.work_title}</h3><div style={{ color: '#64748b', fontSize: 13 }}>Worker: {item.worker_id} · Creator: {item.creator_id} · Reward gross cap: {money(item.reward_amount, item.currency)}</div><pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', background: '#f8fafc', padding: 10, borderRadius: 8, maxHeight: 180, overflow: 'auto' }}>{item.proof}</pre><div style={{ display: 'flex', gap: 8 }}><button disabled={!!busy} style={{ ...button, background: '#166534', color: '#fff' }} onClick={() => review(item.id, 'approved')}>Approve & pay</button><button disabled={!!busy} style={{ ...button, background: '#991b1b', color: '#fff' }} onClick={() => review(item.id, 'rejected')}>Reject</button></div></article>)}
        {!submissions.length && <p style={{ color: '#64748b' }}>No pending worker submissions.</p>}
      </div>
    </section>
  </main>
}
