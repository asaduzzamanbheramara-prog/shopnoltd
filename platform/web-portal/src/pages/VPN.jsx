import React, { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { tryRefresh } from '../lib/tokenRefresh'

const API = import.meta.env.VITE_VPN_API_URL || 'https://vpn.shopnoltd.dpdns.org'
const card = { background: 'white', border: '1px solid #dbeafe', borderRadius: 16, padding: 20, boxShadow: '0 8px 24px rgba(15,23,42,.06)' }

async function request(path, options = {}) {
  let value = localStorage.getItem('shopno_token')
  if (!value) throw new Error('Please log in to use Shopnoltd VPN.')
  const run = token => fetch(`${API}${path}`, { ...options, headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(options.headers || {}), Authorization: `Bearer ${token}` } })
  let response = await run(value)
  if (response.status === 401) { const refreshed = await tryRefresh(); if (refreshed) response = await run(refreshed) }
  const text = await response.text(); let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `VPN request failed (${response.status})`)
  return data
}

function downloadConfig(config, name) {
  const url = URL.createObjectURL(new Blob([config], { type: 'text/plain;charset=utf-8' }))
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url)
}

export default function VPN() {
  const [locations, setLocations] = useState([]), [plans, setPlans] = useState([]), [state, setState] = useState(null)
  const [location, setLocation] = useState(''), [device, setDevice] = useState(''), [result, setResult] = useState(null)
  const [usage, setUsage] = useState(null), [connections, setConnections] = useState([]), [loading, setLoading] = useState(true), [working, setWorking] = useState(false), [error, setError] = useState('')

  const selected = useMemo(() => locations.find(x => x.id === location), [locations, location])
  const available = locations.filter(x => x.available)

  async function load() {
    setLoading(true); setError('')
    try {
      const [l, p, me, u, c] = await Promise.all([fetch(`${API}/api/v1/vpn/locations`).then(r => r.json()), fetch(`${API}/api/v1/vpn/plans`).then(r => r.json()), request('/api/v1/vpn/me'), request('/api/v1/vpn/me/usage'), request('/api/v1/vpn/me/connections')])
      setLocations(l); setPlans(p); setState(me); setUsage(u); setConnections(c)
      if (!location && l.find(x => x.available)) setLocation(l.find(x => x.available).id)
    } catch (e) { setError(e.message) } finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function provision() {
    if (!device.trim() || !location) return
    setWorking(true); setError(''); setResult(null)
    try {
      const data = await request('/api/v1/vpn/me/devices', { method: 'POST', body: JSON.stringify({ device_name: device.trim(), location_id: location }) })
      setResult(data); setDevice(''); await load()
    } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  async function remove(id) {
    if (!window.confirm('Revoke this VPN device? Its configuration will stop working.')) return
    setWorking(true); setError('')
    try { await request(`/api/v1/vpn/me/devices/${id}`, { method: 'DELETE' }); await load() } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  return <main style={{ maxWidth: 1120, margin: '0 auto', padding: '28px 18px 60px' }}>
    <section style={{ ...card, background: 'linear-gradient(135deg,#0f172a,#0369a1)', color: 'white', border: 0, marginBottom: 18 }}>
      <div style={{ fontSize: 42 }}>🔒</div><h1 style={{ margin: '8px 0', fontSize: 'clamp(30px,5vw,48px)' }}>Shopnoltd VPN Provider</h1>
      <p style={{ maxWidth: 820, lineHeight: 1.7, marginBottom: 0 }}>Choose a real Shopnoltd VPN location, provision your device, download its WireGuard configuration, and manage your VPN connection from one account.</p>
    </section>
    {error && <div role="alert" style={{ ...card, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b', marginBottom: 18 }}>{error}</div>}
    {loading ? <div style={card}>Loading your VPN provider account…</div> : <>
      <section style={{ ...card, marginBottom: 18 }}>
        <h2 style={{ marginTop: 0 }}>Choose your VPN location</h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 12 }}>
          {locations.map(x => <button key={x.id} disabled={!x.available} onClick={() => setLocation(x.id)} style={{ textAlign: 'left', padding: 15, borderRadius: 12, border: location === x.id ? '2px solid #0369a1' : '1px solid #cbd5e1', background: x.available ? 'white' : '#f8fafc', cursor: x.available ? 'pointer' : 'not-allowed', opacity: x.available ? 1 : .65 }}>
            <strong>{x.country}</strong><div style={{ color: '#64748b', marginTop: 4 }}>{x.city}</div><div style={{ marginTop: 8, fontSize: 13, fontWeight: 700, color: x.available ? '#166534' : '#64748b' }}>{x.available ? '● Available' : '○ Gateway not deployed'}</div>
          </button>)}
        </div>
        {selected && <p style={{ color: '#475569', marginBottom: 0 }}>Selected: <strong>{selected.country} — {selected.city}</strong>. Locations without a live gateway remain disabled until their real WireGuard infrastructure is deployed.</p>}
      </section>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(300px,1fr))', gap: 18 }}>
        <section style={card}><h2 style={{ marginTop: 0 }}>Devices</h2>
          {state?.devices?.length ? state.devices.map(peer => <div key={peer.id} style={{ padding: '13px 0', borderTop: '1px solid #e2e8f0' }}><strong>{peer.name}</strong><div style={{ color: '#64748b', fontSize: 14 }}>{peer.country || 'VPN'} · {peer.city || peer.location_id} · {peer.address}</div><button disabled={working} onClick={() => remove(peer.id)} style={{ marginTop: 10, padding: '8px 12px', borderRadius: 8, border: '1px solid #fecaca', background: 'white', color: '#b91c1c' }}>Revoke device</button></div>) : <p style={{ color: '#64748b' }}>No active VPN device.</p>}
          {available.length > 0 && !state?.devices?.length && <><label htmlFor="vpn-device"><strong>Device name</strong></label><input id="vpn-device" value={device} onChange={e => setDevice(e.target.value)} placeholder="My Windows PC" maxLength={60} style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 8, padding: 11, border: '1px solid #cbd5e1', borderRadius: 9 }} /><button disabled={working || !device.trim() || !location} onClick={provision} style={{ marginTop: 12, padding: '10px 16px', border: 0, borderRadius: 9, background: '#0369a1', color: 'white', fontWeight: 700 }}>{working ? 'Provisioning…' : 'Create VPN configuration'}</button></>}
        </section>
        <section style={card}><h2 style={{ marginTop: 0 }}>Plan & usage</h2><p><strong>Plan:</strong> {state?.subscription?.name || 'Shopnoltd VPN Free'}</p><p><strong>Device allowance:</strong> {state?.subscription?.max_devices || 1}</p><p><strong>Monthly price:</strong> {state?.subscription?.monthly_price_bdt ?? 0} BDT</p><p><strong>Received:</strong> {Number(usage?.rx_bytes || 0).toLocaleString()} bytes</p><p><strong>Sent:</strong> {Number(usage?.tx_bytes || 0).toLocaleString()} bytes</p><h3>Connection status</h3><p>{connections.some(x => !x.disconnected_at) ? '🟢 Provisioned / gateway session available' : '⚪ No active gateway session reported'}</p></section>
      </div>

      {result?.config && <section style={{ ...card, marginTop: 18, borderColor: '#86efac', background: '#f0fdf4' }}><h2 style={{ marginTop: 0 }}>Configuration ready</h2><p><strong>{result.name}</strong> is assigned to <strong>{result.location.country} — {result.location.city}</strong>.</p><p>Import this file into WireGuard. The private key is generated for this configuration and is returned only in this response.</p><button onClick={() => downloadConfig(result.config, `${result.name.replace(/[^a-z0-9_-]+/gi,'-')}.conf`)} style={{ padding: '11px 16px', border: 0, borderRadius: 9, background: '#166534', color: 'white', fontWeight: 700 }}>Download WireGuard configuration</button></section>}
      <section style={{ ...card, marginTop: 18 }}><h2 style={{ marginTop: 0 }}>Plans</h2><div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(220px,1fr))', gap: 12 }}>{plans.map(p => <div key={p.id} style={{ padding: 15, border: '1px solid #e2e8f0', borderRadius: 12 }}><strong>{p.name}</strong><div style={{ fontSize: 22, fontWeight: 800, marginTop: 6 }}>{p.monthly_price_bdt} BDT<span style={{ fontSize: 12, fontWeight: 400 }}> / month</span></div><div style={{ color: '#64748b', marginTop: 5 }}>{p.max_devices} device{p.max_devices === 1 ? '' : 's'}</div></div>)}</div></section>
    </>}
    <p style={{ marginTop: 24, color: '#64748b', fontSize: 14 }}>Need help? Return to <Link to="/services">Shopnoltd Services</Link>.</p>
  </main>
}
