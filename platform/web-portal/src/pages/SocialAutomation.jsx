import { useCallback, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, Check, Clock3, Pause, Play, Plus, RefreshCw, Trash2, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const card = { border: '1px solid #e5e7eb', borderRadius: 12, padding: 16, background: '#fff' }
const field = { width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #d1d5db', borderRadius: 8 }
const button = { border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 11px', background: '#fff', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 6 }
const dayLabels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export default function SocialAutomation() {
  const [connections, setConnections] = useState([])
  const [schedules, setSchedules] = useState([])
  const [drafts, setDrafts] = useState([])
  const [automationStatus, setAutomationStatus] = useState({ scheduler_enabled: false, executor_enabled: false, publishable_platforms: [] })
  const [connectionIds, setConnectionIds] = useState([])
  const [content, setContent] = useState('')
  const [timezone, setTimezone] = useState('Asia/Dhaka')
  const [times, setTimes] = useState(['09:00', '21:00'])
  const [days, setDays] = useState([0, 1, 2, 3, 4, 5, 6])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState({})

  const load = useCallback(async () => {
    setError('')
    try {
      const status = await platformApi.socialAutomationStatus()
      const safeStatus = status || {
        scheduler_enabled: false, executor_enabled: false, publishable_platforms: [],
      }
      setAutomationStatus(safeStatus)
      if (!safeStatus.scheduler_enabled) {
        setConnections([])
        setSchedules([])
        setDrafts([])
        setConnectionIds([])
        return
      }
      const [accounts, scheduleRows, draftRows] = await Promise.all([
        platformApi.omnichannelConnections(),
        platformApi.socialAutomationSchedules(),
        platformApi.socialAutomationDrafts(),
      ])
      const socialPlatforms = new Set(['facebook', 'instagram', 'youtube', 'tiktok', 'linkedin', 'x'])
      const owned = Array.isArray(accounts)
        ? accounts.filter(x => x.status === 'connected' && x.oauth_authorized === true && socialPlatforms.has(x.platform))
        : []
      setConnections(owned)
      setSchedules(Array.isArray(scheduleRows) ? scheduleRows : [])
      setDrafts(Array.isArray(draftRows) ? draftRows : [])
      setConnectionIds(current => {
        const stillOwned = current.filter(id => owned.some(account => account.id === id))
        return stillOwned.length ? stillOwned : owned.map(account => account.id)
      })
    } catch (e) { setError(e.message) }
  }, [])

  useEffect(() => { load() }, [load])

  const connectionLabel = useMemo(() => {
    const map = new Map(connections.map(c => [c.id, c]))
    return id => {
      const c = map.get(id)
      return c ? c.platform + ' - ' + (c.display_name || c.username || c.platform_account_id) : 'Account unavailable'
    }
  }, [connections])

  async function createSchedules(event) {
    event.preventDefault(); setBusy(true); setError(''); setNotice('')
    try {
      if (!automationStatus.scheduler_enabled) throw new Error('Social automation migration 021 is not installed yet.')
      if (!connectionIds.length) throw new Error('Connect and select at least one platform account first.')
      if (!content.trim()) throw new Error('Post content is required.')
      if (times[0] === times[1]) throw new Error('Choose two different daily times.')
      await platformApi.createSocialAutomationSchedules({
        connection_ids: connectionIds, content_template: content.trim(), timezone,
        times, days_of_week: days, enabled: true,
      })
      setNotice('Schedules saved for ' + connectionIds.length + ' account(s). Each due run creates a draft for your approval, not an automatic post.')
      setContent('')
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function toggleSchedule(item) {
    setBusy(true); setError('')
    try { await platformApi.setSocialAutomationSchedule(item.id, !item.enabled); await load() }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function deleteSchedule(item) {
    if (!window.confirm('Delete this recurring schedule? Existing drafts will remain.')) return
    setBusy(true); setError('')
    try { await platformApi.deleteSocialAutomationSchedule(item.id); await load() }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function saveDraft(item) {
    setBusy(true); setError('')
    try {
      await platformApi.updateSocialAutomationDraft(item.id, editing[item.id] ?? item.content)
      setNotice('Draft saved. Review it before approval.')
      setEditing(current => { const next = { ...current }; delete next[item.id]; return next })
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function approveDraft(item) {
    if (!window.confirm('Approve this exact ' + item.platform + ' post and queue it for publishing?')) return
    setBusy(true); setError(''); setNotice('')
    try {
      await platformApi.approveSocialAutomationDraft(item.id)
      setNotice('Approved and queued. Publishing still requires a valid connection and provider permission.')
      await load()
    } catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  async function rejectDraft(item) {
    setBusy(true); setError('')
    try { await platformApi.rejectSocialAutomationDraft(item.id); await load() }
    catch (e) { setError(e.message) } finally { setBusy(false) }
  }

  function toggleDay(day) {
    setDays(current => current.includes(day) ? current.filter(x => x !== day) : [...current, day].sort())
  }

  return <main style={{ maxWidth: 1120, margin: '0 auto', padding: 24, display: 'grid', gap: 18 }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
      <div>
        <Link to="/connections" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', color: '#374151', textDecoration: 'none', marginBottom: 12 }}><ArrowLeft size={16} /> Platform connections</Link>
        <h1 style={{ margin: 0 }}>Social Automation Center</h1>
        <p style={{ color: '#6b7280', margin: '6px 0 0' }}>Two daily draft runs, an approval inbox, and account-level controls.</p>
      </div>
      <button type="button" onClick={load} disabled={busy} style={button}><RefreshCw size={15} /> Refresh</button>
    </div>
    {error && <div role="alert" style={{ padding: 12, background: '#fef2f2', color: '#991b1b', borderRadius: 8 }}>{error}</div>}
    {notice && <div role="status" style={{ padding: 12, background: '#f0fdf4', color: '#166534', borderRadius: 8 }}>{notice}</div>}
    {!automationStatus.scheduler_enabled && <div role="alert" style={{ padding: 12, background: '#fef2f2', color: '#991b1b', borderRadius: 8 }}>Social automation database migration is not ready. Scheduling is unavailable until migration 021 is applied.</div>}
    {automationStatus.scheduler_enabled && !automationStatus.executor_enabled && <div role="status" style={{ padding: 12, background: '#fffbeb', color: '#92400e', borderRadius: 8 }}>Draft scheduling is available. External publishing is disabled on the server until provider sandbox validation is completed.</div>}

    <section style={card}>
      <h2 style={{ margin: '0 0 8px', fontSize: 19 }}>Create a twice-daily schedule</h2>
      <p style={{ margin: '0 0 14px', color: '#6b7280', lineHeight: 1.5 }}>Each selected time creates a new draft in your approval inbox. Publishing is never automatic. Use content you own or are authorized to publish.</p>
      {!connections.length && <p style={{ color: '#92400e' }}>No OAuth-authorized account is available. <Link to="/connections">Connect a platform account</Link> first.</p>}
      <form onSubmit={createSchedules} style={{ display: 'grid', gap: 12 }}>
        <label>Connected accounts <span style={{ color: '#6b7280', fontWeight: 400 }}>(all authorized accounts are selected by default)</span>
          <select multiple required value={connectionIds} onChange={e => setConnectionIds(Array.from(e.target.selectedOptions, option => option.value))} style={{ ...field, minHeight: 112 }}>
            {connections.map(c => <option key={c.id} value={c.id}>{c.platform} - {c.display_name || c.username || c.platform_account_id}</option>)}
          </select>
        </label>
        <div style={{ display: 'flex', gap: 8 }}>
          <button type="button" style={button} onClick={() => setConnectionIds(connections.map(c => c.id))}>Select all</button>
          <button type="button" style={button} onClick={() => setConnectionIds([])}>Clear selection</button>
        </div>
        <label>Post template
          <textarea required maxLength={10000} rows={5} value={content} onChange={e => setContent(e.target.value)} placeholder="Write the post content copied into each scheduled draft." style={{ ...field, resize: 'vertical' }} />
        </label>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 12 }}>
          <label>First daily time <input type="time" value={times[0]} onChange={e => setTimes([e.target.value, times[1]])} style={field} /></label>
          <label>Second daily time <input type="time" value={times[1]} onChange={e => setTimes([times[0], e.target.value])} style={field} /></label>
          <label>Timezone <input value={timezone} onChange={e => setTimezone(e.target.value)} placeholder="Asia/Dhaka" style={field} /></label>
        </div>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 7 }}>Run on</div>
          <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap' }}>
            {dayLabels.map((label, index) => <button key={label} type="button" aria-pressed={days.includes(index)} onClick={() => toggleDay(index)} style={{ ...button, background: days.includes(index) ? '#111827' : '#fff', color: days.includes(index) ? '#fff' : '#374151' }}>{label}</button>)}
          </div>
        </div>
        <button type="submit" disabled={busy || !automationStatus.scheduler_enabled || !connections.length || !connectionIds.length || !days.length} style={{ ...button, width: 'fit-content', background: '#111827', color: '#fff', borderColor: '#111827' }}><Plus size={15} /> {busy ? 'Saving...' : 'Create two daily schedules'}</button>
      </form>
    </section>

    <section style={card}>
      <h2 style={{ margin: '0 0 12px', fontSize: 19 }}>Your schedules ({schedules.length})</h2>
      <div style={{ display: 'grid', gap: 10 }}>
        {schedules.map(item => <article key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 9, padding: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <strong>{item.platform} - {String(item.local_time).slice(0, 5)} ({item.timezone})</strong>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{connectionLabel(item.connection_id)} - Next run: {item.next_run_at ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', timeZone: item.timezone }).format(new Date(item.next_run_at)) : 'Not scheduled'}</div>
            <div style={{ fontSize: 12, color: '#6b7280', marginTop: 4 }}>{(item.days_of_week || []).map(x => dayLabels[x]).join(', ')}</div>
            {item.paused_reason && <div style={{ fontSize: 12, color: '#92400e', marginTop: 4 }}>{item.paused_reason}</div>}
          </div>
          <div style={{ display: 'flex', gap: 7 }}>
            <button type="button" disabled={busy} onClick={() => toggleSchedule(item)} style={button}>{item.enabled ? <Pause size={14} /> : <Play size={14} />}{item.enabled ? 'Pause' : 'Enable'}</button>
            <button type="button" disabled={busy} onClick={() => deleteSchedule(item)} style={{ ...button, color: '#991b1b' }}><Trash2 size={14} /> Delete</button>
          </div>
        </article>)}
        {!schedules.length && <p style={{ color: '#6b7280' }}>No recurring schedules yet.</p>}
      </div>
    </section>

    <section style={card}>
      <h2 style={{ margin: '0 0 12px', fontSize: 19 }}>Draft approval inbox ({drafts.length})</h2>
      <p style={{ margin: '0 0 14px', color: '#6b7280' }}>Only X and LinkedIn currently have publishing adapters in this repository. Other platforms may hold drafts, but cannot be approved for external publishing until their official API adapters are implemented and tested.</p>
      {!automationStatus.executor_enabled && <p role="status" style={{ padding: 10, borderRadius: 8, background: '#fffbeb', color: '#92400e' }}>Publishing is currently disabled by the server. Schedules can create drafts, but no post can be queued or published until the executor is deliberately enabled after sandbox validation.</p>}
      {automationStatus.executor_requested && !automationStatus.token_encryption_configured && <p role="alert" style={{ padding: 10, borderRadius: 8, background: '#fef2f2', color: '#991b1b' }}>Publishing is unavailable because provider-token encryption is not configured.</p>}
      <div style={{ display: 'grid', gap: 12 }}>
        {drafts.map(item => <article key={item.id} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 13 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap' }}>
            <strong>{item.platform} - {item.status}</strong>
            <span style={{ fontSize: 12, color: '#6b7280' }}>{connectionLabel(item.connection_id)}{item.scheduled_for ? ' - ' + new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short', ...(item.schedule_timezone ? { timeZone: item.schedule_timezone } : {}) }).format(new Date(item.scheduled_for)) : ''}</span>
          </div>
          {['draft', 'pending_approval', 'rejected'].includes(item.status) ? <>
            <textarea rows={4} value={editing[item.id] ?? item.content} onChange={e => setEditing(current => ({ ...current, [item.id]: e.target.value }))} style={{ ...field, marginTop: 10, resize: 'vertical' }} />
            <div style={{ display: 'flex', gap: 7, flexWrap: 'wrap', marginTop: 9 }}>
              <button type="button" disabled={busy || (Object.prototype.hasOwnProperty.call(editing, item.id) && editing[item.id] === item.content)} onClick={() => saveDraft(item)} style={button}><Check size={14} /> Save edits</button>
              {automationStatus.publishable_platforms?.includes(item.platform) && <button type="button" disabled={busy || !automationStatus.executor_enabled || !automationStatus.publishable_platforms?.includes(item.platform) || (Object.prototype.hasOwnProperty.call(editing, item.id) && editing[item.id] !== item.content)} title={Object.prototype.hasOwnProperty.call(editing, item.id) && editing[item.id] !== item.content ? 'Save edits before approving this draft' : 'Approve the saved draft'} onClick={() => approveDraft(item)} style={{ ...button, background: '#111827', color: '#fff', opacity: automationStatus.executor_enabled ? 1 : 0.55 }}><Check size={14} /> Approve & queue</button>}
              <button type="button" disabled={busy} onClick={() => rejectDraft(item)} style={{ ...button, color: '#991b1b' }}><X size={14} /> Reject</button>
            </div>
          </> : <p style={{ whiteSpace: 'pre-wrap', marginBottom: 0 }}>{item.content}</p>}
          {item.error_message && <p style={{ color: '#991b1b', fontSize: 12 }}>{item.error_message}</p>}
        </article>)}
        {!drafts.length && <p style={{ color: '#6b7280' }}>No drafts waiting for review.</p>}
      </div>
    </section>
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, color: '#6b7280', fontSize: 12 }}><Clock3 size={14} /> Scheduler timezone defaults to Asia/Dhaka. Approval is required for every external post.</div>
  </main>
}
