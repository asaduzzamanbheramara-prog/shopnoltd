import { useCallback, useEffect, useRef, useState } from 'react'
import { Bot, Check, FileText, RefreshCw, Send, X } from 'lucide-react'
import { tryRefresh } from '../lib/tokenRefresh'

// Agent mode: talks to agent-service (/ws/ui). Auth is the same Keycloak access token the
// rest of the portal already keeps in localStorage ('shopno_token'); nothing new is stored.
const AGENT_WS_URL = 'wss://agent.shopnoltd.dpdns.org/ws/ui'
const MODELS = [
  { id: 'claude-sonnet', label: 'Manual · Claude Sonnet' },
  { id: 'auto', label: 'Auto · model rotation' }
]
const STATUS_LABEL = {
  connecting: 'Connecting…',
  connected: 'Connected',
  disconnected: 'Disconnected · reconnecting…',
  auth_failed: 'Please sign in again',
  forbidden: 'This page is not allowed to use the agent'
}

function tokenExpiresInMs(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload.exp * 1000 - Date.now()
  } catch { return 0 }
}

async function freshToken() {
  let token = localStorage.getItem('shopno_token')
  if (!token || tokenExpiresInMs(token) < 60000) {
    token = (await tryRefresh()) || localStorage.getItem('shopno_token')
  }
  return token && tokenExpiresInMs(token) > 0 ? token : null
}

function describeApproval(tool, args) {
  if (!args) return tool
  if (args.action === 'open') return `Open this page in your browser:\n${args.url}`
  if (args.action === 'click') return `Click this element:\n${args.selector}`
  if (args.action === 'type') return `Type into: ${args.selector}\n\n“${String(args.text || '').slice(0, 300)}”`
  return JSON.stringify(args, null, 2).slice(0, 600)
}

const card = { border: '1px solid #e5e7eb', borderRadius: 12, padding: '10px 12px', background: '#fff', fontSize: 14 }
const smallBtn = { border: '1px solid #d1d5db', background: '#fff', borderRadius: 8, padding: '6px 12px', cursor: 'pointer', fontWeight: 600, fontSize: 13 }

function PlanCard({ plan }) {
  if (!plan.length) return null
  const done = plan.filter((step) => step.status === 'done').length
  return (
    <div style={{ ...card, background: '#f9fafb' }}>
      <div style={{ fontWeight: 700, marginBottom: 6 }}>Plan · {done}/{plan.length} done</div>
      {plan.map((step, index) => (
        <div key={index} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', padding: '3px 0', color: step.status === 'done' ? '#6b7280' : '#111827' }}>
          <span style={{ width: 18, flex: '0 0 18px', textAlign: 'center' }}>{step.status === 'done' ? <Check size={14} color="#10a37f" /> : step.status === 'doing' ? '▶' : '○'}</span>
          <span style={{ textDecoration: step.status === 'done' ? 'line-through' : 'none', fontWeight: step.status === 'doing' ? 700 : 400 }}>{step.title}</span>
        </div>
      ))}
    </div>
  )
}

function ToolCard({ item }) {
  const [open, setOpen] = useState(false)
  const summary = item.args?.action ? `${item.name} · ${item.args.action}` : item.name
  const target = item.args?.url || item.args?.selector || item.args?.path || item.args?.command || ''
  return (
    <div style={{ ...card, background: '#f9fafb' }}>
      <button type="button" onClick={() => setOpen((value) => !value)} style={{ border: 0, background: 'transparent', padding: 0, cursor: 'pointer', textAlign: 'left', width: '100%', display: 'flex', gap: 8, alignItems: 'center', font: 'inherit' }}>
        <span style={{ fontWeight: 700 }}>{summary}</span>
        <span style={{ color: '#6b7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{String(target).slice(0, 120)}</span>
        <span style={{ color: item.result === null ? '#b45309' : '#10a37f', fontSize: 12 }}>{item.result === null ? 'running…' : 'done'}</span>
      </button>
      {open && <pre style={{ margin: '8px 0 0', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontSize: 12, color: '#374151', maxHeight: 260, overflow: 'auto' }}>{JSON.stringify(item.args, null, 2)}{item.result !== null ? `\n\n→ ${item.result}` : ''}</pre>}
    </div>
  )
}

function ApprovalCard({ item, onRespond }) {
  const pending = item.state === 'pending'
  return (
    <div style={{ ...card, border: '2px solid #f59e0b', background: '#fffbeb' }} role="alertdialog" aria-label="Approval needed">
      <div style={{ fontWeight: 700, marginBottom: 6 }}>The agent wants your approval</div>
      <pre style={{ margin: '0 0 10px', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', font: 'inherit', fontSize: 13 }}>{describeApproval(item.tool, item.args)}</pre>
      {pending ? (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button type="button" onClick={() => onRespond(item, true)} style={{ ...smallBtn, background: '#10a37f', color: '#fff', borderColor: '#10a37f' }}>Allow once</button>
          <button type="button" onClick={() => onRespond(item, false)} style={smallBtn}>Deny</button>
          <span style={{ fontSize: 12, color: '#92400e' }}>Expires in 2 minutes</span>
        </div>
      ) : <div style={{ fontSize: 13, color: '#6b7280' }}>{item.state === 'allowed' ? 'Allowed' : item.state === 'denied' ? 'Denied' : 'Expired'}</div>}
    </div>
  )
}

export default function AgentWorkspace() {
  const [status, setStatus] = useState('connecting')
  const [model, setModel] = useState('claude-sonnet')
  const [goal, setGoal] = useState('')
  const [running, setRunning] = useState(false)
  const [plan, setPlan] = useState([])
  const [items, setItems] = useState([])
  const wsRef = useRef(null)
  const genRef = useRef(0)
  const aliveRef = useRef(false)
  const retryRef = useRef(0)
  const timerRef = useRef(null)
  const idRef = useRef(0)
  const scrollRef = useRef(null)

  const push = useCallback((entry) => setItems((current) => [...current, { id: ++idRef.current, ...entry }]), [])

  const handle = useCallback((m) => {
    switch (m.type) {
      case 'auth_ok': setStatus('connected'); retryRef.current = 0; break
      case 'text': push({ kind: 'text', text: String(m.text || '') }); break
      case 'plan': setPlan(Array.isArray(m.steps) ? m.steps.slice(0, 20) : []); break
      case 'tool':
        if (m.name !== 'update_plan') push({ kind: 'tool', name: m.name, args: m.args, result: null })
        break
      case 'result':
        setItems((current) => {
          for (let i = current.length - 1; i >= 0; i -= 1) {
            const it = current[i]
            if (it.kind === 'tool' && it.name === m.name && it.result === null) {
              const copy = [...current]
              copy[i] = { ...it, result: String(m.result ?? '') }
              return copy
            }
          }
          return current
        })
        break
      case 'file': push({ kind: 'file', path: String(m.path || '') }); break
      case 'screenshot':
        if (typeof m.image === 'string' && m.image.startsWith('data:image/jpeg;base64,')) push({ kind: 'shot', image: m.image })
        break
      case 'approval': push({ kind: 'approval', approvalId: m.id, tool: m.tool, args: m.args, state: 'pending' }); break
      case 'error': push({ kind: 'error', text: String(m.text || 'Something went wrong.') }); break
      case 'done': setRunning(false); break
      default: break
    }
  }, [push])

  const connect = useCallback(async () => {
    if (!aliveRef.current) return
    const gen = ++genRef.current
    setStatus('connecting')
    const token = await freshToken()
    if (gen !== genRef.current) return
    if (!token) { setStatus('auth_failed'); return }
    const ws = new WebSocket(AGENT_WS_URL)
    wsRef.current = ws
    ws.onopen = () => ws.send(JSON.stringify({ type: 'auth', token }))
    ws.onmessage = (event) => {
      let message
      try { message = JSON.parse(event.data) } catch { return }
      if (message && typeof message === 'object') handle(message)
    }
    ws.onclose = (event) => {
      if (gen !== genRef.current) return
      wsRef.current = null
      setRunning(false)
      setItems((current) => current.map((it) => (it.kind === 'approval' && it.state === 'pending' ? { ...it, state: 'expired' } : it)))
      if (!aliveRef.current) return
      if (event.code === 4403) { setStatus('forbidden'); return }
      setStatus('disconnected')
      const delay = Math.min(30000, 1000 * 2 ** retryRef.current)
      retryRef.current += 1
      timerRef.current = setTimeout(connect, delay)
    }
    ws.onerror = () => {}
  }, [handle])

  useEffect(() => {
    aliveRef.current = true
    connect()
    return () => {
      aliveRef.current = false
      genRef.current += 1
      clearTimeout(timerRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [connect])

  // Keep the socket warm (Cloudflare drops idle sockets) and extend the server-side session.
  useEffect(() => {
    const ping = setInterval(() => {
      const ws = wsRef.current
      if (ws?.readyState === 1) ws.send(JSON.stringify({ ping: 1 }))
    }, 25000)
    const refresh = setInterval(async () => {
      const ws = wsRef.current
      if (ws?.readyState !== 1) return
      const token = await freshToken()
      if (token && ws.readyState === 1) ws.send(JSON.stringify({ type: 'auth', token }))
    }, 4 * 60 * 1000)
    return () => { clearInterval(ping); clearInterval(refresh) }
  }, [])

  useEffect(() => {
    const element = scrollRef.current
    if (element) element.scrollTo({ top: element.scrollHeight, behavior: 'smooth' })
  }, [items.length, plan])

  function respond(item, approved) {
    const ws = wsRef.current
    if (ws?.readyState !== 1) return
    ws.send(JSON.stringify({ type: 'approval', id: item.approvalId, approved }))
    setItems((current) => current.map((it) => (it.id === item.id ? { ...it, state: approved ? 'allowed' : 'denied' } : it)))
  }

  function send() {
    const text = goal.trim()
    const ws = wsRef.current
    if (!text || running || status !== 'connected' || ws?.readyState !== 1) return
    push({ kind: 'user', text })
    setPlan([])
    setRunning(true)
    ws.send(JSON.stringify({ goal: text, model }))
    setGoal('')
  }

  const connected = status === 'connected'

  return (
    <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', background: '#fff' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 18px', borderBottom: '1px solid #e5e7eb', flexWrap: 'wrap' }}>
        <span style={{ width: 9, height: 9, borderRadius: 99, background: connected ? '#10a37f' : status === 'connecting' ? '#f59e0b' : '#ef4444' }} />
        <span style={{ fontSize: 13, color: '#4b5563', marginRight: 'auto' }}>{STATUS_LABEL[status] || status}</span>
        <label style={{ fontSize: 13, color: '#4b5563' }}>Model{' '}
          <select value={model} onChange={(event) => setModel(event.target.value)} disabled={running} aria-label="Agent model" style={{ padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 8, background: '#fff', fontWeight: 600 }}>
            {MODELS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
          </select>
        </label>
        {(status === 'disconnected' || status === 'auth_failed') && <button type="button" onClick={() => { retryRef.current = 0; clearTimeout(timerRef.current); connect() }} style={{ ...smallBtn, display: 'inline-flex', alignItems: 'center', gap: 5 }}><RefreshCw size={13} /> Reconnect</button>}
      </div>

      <div ref={scrollRef} style={{ flex: 1, minHeight: 0, overflowY: 'auto', overscrollBehavior: 'contain', padding: '14px max(18px, calc((100% - 820px) / 2))' }}>
        {!items.length && (
          <div style={{ textAlign: 'center', padding: '40px 10px', color: '#6b7280' }}>
            <div style={{ width: 54, height: 54, margin: '0 auto 16px', borderRadius: 16, display: 'grid', placeItems: 'center', background: '#10a37f', color: '#fff' }}><Bot size={28} /></div>
            <h2 style={{ margin: '0 0 8px', color: '#111827' }}>Give the agent a goal</h2>
            <p style={{ margin: 0 }}>It plans the steps, works in its own workspace, and asks before it opens pages or clicks in your browser.</p>
            <p style={{ margin: '10px 0 0', fontSize: 13 }}>Browser actions run in an isolated Shopnoltd Chromium session. Opening pages, clicking and typing require your approval.</p>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {items.map((item) => {
            if (item.kind === 'user') return <div key={item.id} style={{ alignSelf: 'flex-end', maxWidth: '88%', background: '#111827', color: '#fff', borderRadius: 14, padding: '9px 14px', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.text}</div>
            if (item.kind === 'text') return <div key={item.id} style={{ lineHeight: 1.6, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.text}</div>
            if (item.kind === 'tool') return <ToolCard key={item.id} item={item} />
            if (item.kind === 'approval') return <ApprovalCard key={item.id} item={item} onRespond={respond} />
            if (item.kind === 'file') return <div key={item.id} style={{ ...card, display: 'flex', alignItems: 'center', gap: 8 }}><FileText size={15} /> <span>File saved: <b>{item.path}</b></span></div>
            if (item.kind === 'shot') return <img key={item.id} src={item.image} alt="Browser screenshot" style={{ maxWidth: '100%', borderRadius: 10, border: '1px solid #e5e7eb' }} />
            if (item.kind === 'error') return <div key={item.id} role="alert" style={{ ...card, background: '#fef2f2', color: '#991b1b', borderColor: '#fecaca', display: 'flex', gap: 8 }}><X size={15} style={{ flex: '0 0 auto', marginTop: 2 }} />{item.text}</div>
            return null
          })}
          {plan.length > 0 && <div style={{ position: 'sticky', bottom: 0 }}><PlanCard plan={plan} /></div>}
          {running && <div style={{ color: '#6b7280', fontSize: 13 }}>Working…</div>}
        </div>
      </div>

      <div style={{ padding: '10px max(18px, calc((100% - 820px) / 2)) 16px', borderTop: '1px solid #f3f4f6' }}>
        <form onSubmit={(event) => { event.preventDefault(); send() }} style={{ position: 'relative', border: '1px solid #d1d5db', borderRadius: 16, boxShadow: '0 2px 8px rgba(0,0,0,.06)', background: '#fff' }}>
          <textarea value={goal} onChange={(event) => setGoal(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send() } }} rows={2} maxLength={4000} placeholder={connected ? 'Describe what the agent should do…' : 'Waiting for connection…'} disabled={!connected || running} style={{ display: 'block', width: '100%', boxSizing: 'border-box', border: 0, outline: 0, resize: 'none', borderRadius: 16, padding: '14px 56px 14px 16px', font: 'inherit', lineHeight: 1.45 }} />
          <button type="submit" disabled={!connected || running || !goal.trim()} aria-label="Send goal" title="Send" style={{ position: 'absolute', right: 9, bottom: 9, width: 36, height: 36, border: 0, borderRadius: 10, display: 'grid', placeItems: 'center', background: !connected || running || !goal.trim() ? '#d1d5db' : '#111827', color: '#fff', cursor: 'pointer' }}><Send size={17} /></button>
        </form>
        <div style={{ textAlign: 'center', fontSize: 11, color: '#9ca3af', marginTop: 8 }}>Enter to send · The agent runs one task at a time · Opening pages, clicking and typing always ask first</div>
      </div>
    </div>
  )
}
