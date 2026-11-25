import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { RefreshCw, Monitor, Plus, Trash2, Copy, ShieldCheck, ExternalLink } from 'lucide-react'
import { tryRefresh } from '../lib/tokenRefresh'
import { isPlatformAdmin } from '../lib/jwt'

const API = 'https://devices.shopnoltd.dpdns.org'
const shell = { maxWidth: 1180, margin: '0 auto', padding: '28px 16px 80px', fontFamily: 'system-ui, sans-serif', color: '#172033' }
const card = { background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 18, marginBottom: 14 }
const button = { display: 'inline-flex', alignItems: 'center', gap: 7, border: 0, borderRadius: 8, padding: '9px 12px', background: '#0f172a', color: '#fff', cursor: 'pointer', fontWeight: 650 }
const input = { padding: '10px 12px', border: '1px solid #cbd5e1', borderRadius: 8, minWidth: 0, font: 'inherit' }

async function request(path, options = {}) {
  let token = localStorage.getItem('shopno_token')
  if (!token) throw new Error('Please sign in to your Shopnoltd account.')
  const send = (value) => fetch(API + path, {
    ...options,
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}), Authorization: `Bearer ${value}` },
  })
  let response = await send(token)
  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) response = await send(refreshed)
  }
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `Device service returned ${response.status}`)
  return data
}

function DeviceCard({ device, admin, onDelete, onShare, onToken, onConnect }) {
  const [busy, setBusy] = useState(false)
  return <article style={card}>
    <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', flexWrap: 'wrap' }}>
      <Monitor size={22} color="#0369a1" />
      <div style={{ flex: 1, minWidth: 180 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>{device.name || 'Unnamed device'}</h2>
        <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{device.platform || 'Unknown platform'} · {device.status || 'status unknown'}</div>
      </div>
      <span style={{ borderRadius: 20, padding: '4px 9px', background: device.status === 'online' ? '#dcfce7' : '#f1f5f9', color: '#334155', fontSize: 12 }}>{device.executor_enabled ? 'Agent enrolled' : 'Not enrolled'}</span>
    </div>
    <dl style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 9, margin: '16px 0', fontSize: 13 }}>
      <div><dt style={{ color: '#64748b' }}>Device ID</dt><dd style={{ margin: '3px 0', overflowWrap: 'anywhere' }}>{device.id}</dd></div>
      {admin && <div><dt style={{ color: '#64748b' }}>Owner subject</dt><dd style={{ margin: '3px 0', overflowWrap: 'anywhere' }}>{device.owner_id || 'Unavailable'}</dd></div>}
      <div><dt style={{ color: '#64748b' }}>Hostname</dt><dd style={{ margin: '3px 0' }}>{device.hostname || 'Not reported'}</dd></div>
      <div><dt style={{ color: '#64748b' }}>MeshCentral</dt><dd style={{ margin: '3px 0' }}>{device.meshcentral_node_id ? 'Linked' : 'Not linked'}</dd></div>
    </dl>
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
      {!admin && !device.shared_access && !device.executor_enabled && <button type="button" style={button} disabled={busy} onClick={async () => { setBusy(true); try { await onToken(device) } finally { setBusy(false) } }}>Get enrollment token</button>}
      {!admin && !device.shared_access && <button type="button" style={{ ...button, background: '#334155' }} onClick={() => onShare(device)}>Share device</button>}
      {device.meshcentral_node_id && <button type="button" style={{ ...button, background: '#0369a1' }} onClick={() => onConnect(device)}><ExternalLink size={15}/> Connect</button>}
      {!device.shared_access && <button type="button" style={{ ...button, background: '#b91c1c' }} onClick={() => onDelete(device)}><Trash2 size={15}/> {admin ? 'Revoke device' : 'Remove device'}</button>}
    </div>
  </article>
}

export default function Devices({ admin = false }) {
  const platformAdmin = isPlatformAdmin()
  const adminView = admin && platformAdmin
  const [devices, setDevices] = useState([])
  const [name, setName] = useState('')
  const [platform, setPlatform] = useState('windows')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [tokenResult, setTokenResult] = useState('')

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const result = await request('/api/devices')
      setDevices(Array.isArray(result) ? result : [])
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  async function addDevice(event) {
    event.preventDefault(); setError(''); setNotice(''); setTokenResult('')
    if (!name.trim()) return setError('Enter a name for this device.')
    try {
      const result = await request('/api/devices', { method: 'POST', body: JSON.stringify({ name: name.trim(), platform }) })
      setTokenResult(result.enrollment_token || '')
      setNotice('Device registered to your account. Keep the one-time token private and enter it only in the official device installer.')
      setName('')
      await load()
    } catch (e) { setError(e.message) }
  }

  async function deleteDevice(device) {
    if (!window.confirm(`Remove ${device.name || 'this device'}? This revokes its Shopnoltd device registration.`)) return
    try { await request('/api/devices/' + encodeURIComponent(device.id), { method: 'DELETE' }); setNotice('Device registration revoked.'); await load() }
    catch (e) { setError(e.message) }
  }

  async function createToken(device) {
    try {
      const result = await request('/api/devices/' + encodeURIComponent(device.id) + '/enrollment-token', { method: 'POST' })
      setTokenResult(result.enrollment_token || '')
      setNotice('A new one-time enrollment token was issued. Any previous pending token may no longer work.')
    } catch (e) { setError(e.message) }
  }

  async function shareDevice(device) {
    const raw = window.prompt('Invitation expiry in hours (1–168):', '24')
    if (raw === null) return
    const hours = Number(raw)
    if (!Number.isInteger(hours) || hours < 1 || hours > 168) return setError('Enter a whole number between 1 and 168.')
    try {
      const result = await request('/api/devices/' + encodeURIComponent(device.id) + '/shares', { method: 'POST', body: JSON.stringify({ expires_in_hours: hours }) })
      setTokenResult(result.share_url || '')
      setNotice('Single-use invitation created. Share it only with the intended Shopnoltd user.')
    } catch (e) { setError(e.message) }
  }

  async function connectDevice(device) {
    const popup = window.open('about:blank', '_blank', 'noopener,noreferrer')
    try {
      const result = await request('/api/connect/' + encodeURIComponent(device.id))
      if (!result.connect_url) throw new Error('Gateway did not return a connection URL.')
      if (popup) popup.location = result.connect_url
      else window.location.assign(result.connect_url)
    } catch (e) {
      if (popup) popup.close()
      setError(e.message)
    }
  }

  async function copy(value) {
    try { await navigator.clipboard.writeText(value); setNotice('Copied to clipboard.') }
    catch { window.prompt('Copy this value:', value) }
  }

  return <main style={shell}>
    <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap', marginBottom: 18 }}>
      <div style={{ marginRight: 'auto' }}>
        <h1 style={{ margin: 0 }}>{adminView ? 'Authorized Devices' : 'My Devices'}</h1>
        <p style={{ margin: '6px 0 0', color: '#64748b' }}>{adminView ? 'Platform-wide device registry. Device actions are audited by the gateway.' : 'Connect and manage devices registered to your Shopnoltd account.'}</p>
      </div>
      <button type="button" style={button} onClick={load} disabled={loading}><RefreshCw size={15}/> Refresh</button>
      <Link to="/account">Account settings</Link>
    </div>

    {error && <div role="alert" style={{ ...card, borderColor: '#fecaca', color: '#991b1b' }}>{error}</div>}
    {notice && <div role="status" style={{ ...card, borderColor: '#bbf7d0', color: '#166534' }}>{notice}</div>}
    {tokenResult && <div style={{ ...card, borderColor: '#93c5fd' }}>
      <b>{tokenResult.startsWith('http') ? 'Single-use device invitation' : 'One-time enrollment token'}</b>
      <p style={{ color: '#64748b', fontSize: 13 }}>This value is shown once. Do not post it publicly or send it to anyone except the intended device/user.</p>
      <code style={{ display: 'block', overflowWrap: 'anywhere', padding: 10, background: '#f1f5f9', borderRadius: 8 }}>{tokenResult}</code>
      <button type="button" style={{ ...button, marginTop: 10 }} onClick={() => copy(tokenResult)}><Copy size={15}/> Copy</button>
      <button type="button" style={{ ...button, marginTop: 10, marginLeft: 8, background: '#475569' }} onClick={() => setTokenResult('')}>Hide</button>
    </div>}

    {!adminView && <form onSubmit={addDevice} style={{ ...card, display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10, alignItems: 'end' }}>
      <label style={{ display: 'grid', gap: 5, fontSize: 13 }}>Device name<input style={input} value={name} onChange={e => setName(e.target.value)} placeholder="e.g. My Windows PC" maxLength={80}/></label>
      <label style={{ display: 'grid', gap: 5, fontSize: 13 }}>Platform<select style={input} value={platform} onChange={e => setPlatform(e.target.value)}><option value="windows">Windows</option><option value="linux">Linux</option><option value="macos">macOS</option><option value="android">Android</option><option value="ios">iPhone / iPad</option><option value="browser">Browser</option><option value="other">Other</option></select></label>
      <button type="submit" style={button}><Plus size={16}/> Connect Device</button>
    </form>}

    <div style={{ display: 'flex', gap: 8, alignItems: 'center', margin: '18px 0 12px', color: '#475569' }}><ShieldCheck size={17}/><b>{devices.length} {adminView ? 'registered devices across Shopnoltd' : 'devices available to your account'}</b></div>
    {loading ? <div style={card}>Loading devices…</div> : devices.length ? devices.map(device => <DeviceCard key={device.id} device={device} admin={adminView} onDelete={deleteDevice} onShare={shareDevice} onToken={createToken} onConnect={connectDevice}/>) : <div style={card}><h2 style={{ marginTop: 0 }}>No devices registered</h2><p style={{ color: '#64748b' }}>Add a device above to create its account-owned enrollment record. An agent must be installed separately before the device can report online.</p></div>}
    <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.6 }}>Security: ownership is assigned by the authenticated gateway, not by browser-supplied user IDs. Remote control is available only after a device agent is enrolled and linked. Android/iOS support depends on a compatible native agent and platform permissions.</p>
  </main>
}
