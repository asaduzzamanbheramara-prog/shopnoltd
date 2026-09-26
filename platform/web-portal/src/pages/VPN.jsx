import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { tryRefresh } from '../lib/tokenRefresh'

const API = import.meta.env.VITE_VPN_API_URL || 'https://vpn.shopnoltd.dpdns.org'
const card = { background: 'white', border: '1px solid #dbeafe', borderRadius: 16, padding: 20, boxShadow: '0 8px 24px rgba(15,23,42,.06)' }

async function token() {
  let value = localStorage.getItem('shopno_token')
  if (!value) throw new Error('Please log in to use Shopnoltd VPN.')
  return value
}

async function request(path, options = {}) {
  let value = await token()
  const run = (t) => fetch(`${API}${path}`, { ...options, headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(options.headers || {}), Authorization: `Bearer ${t}` } })
  let response = await run(value)
  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) response = await run(refreshed)
  }
  const text = await response.text()
  let data = null
  try { data = text ? JSON.parse(text) : null } catch { data = text }
  if (!response.ok) throw new Error(data?.detail || data?.message || `VPN request failed (${response.status})`)
  return data
}

function downloadConfig(config, name = 'shopnoltd-vpn.conf') {
  const blob = new Blob([config], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

export default function VPN() {
  const [state, setState] = useState(null)
  const [device, setDevice] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')

  async function load() {
    setLoading(true); setError('')
    try { setState(await request('/api/v1/vpn/me')) }
    catch (e) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function provision() {
    if (!device.trim()) return
    setWorking(true); setError(''); setResult(null)
    try {
      const data = await request('/api/v1/vpn/me/peers', { method: 'POST', body: JSON.stringify({ device_name: device.trim() }) })
      setResult(data); setDevice(''); await load()
    } catch (e) { setError(e.message) }
    finally { setWorking(false) }
  }

  async function remove(peerId) {
    if (!window.confirm('Remove this VPN device? Its configuration will stop working.')) return
    setWorking(true); setError('')
    try { await request(`/api/v1/vpn/me/peers/${peerId}`, { method: 'DELETE' }); await load() }
    catch (e) { setError(e.message) }
    finally { setWorking(false) }
  }

  return <main style={{ maxWidth: 1050, margin: '0 auto', padding: '28px 18px 60px' }}>
    <section style={{ ...card, background: 'linear-gradient(135deg,#0f172a,#0369a1)', color: 'white', border: 0, marginBottom: 18 }}>
      <div style={{ fontSize: 42 }}>🔒</div>
      <h1 style={{ margin: '8px 0', fontSize: 'clamp(30px,5vw,48px)' }}>Shopnoltd VPN</h1>
      <p style={{ maxWidth: 760, lineHeight: 1.7, marginBottom: 0 }}>Secure your device with a Shopnoltd WireGuard connection. Sign in, provision one device, download its private configuration, and connect with the official WireGuard client.</p>
    </section>
    {error && <div role="alert" style={{ ...card, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b', marginBottom: 18 }}>{error}</div>}
    {loading ? <div style={card}>Loading your VPN account…</div> : <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 18 }}>
      <section style={card}>
        <h2 style={{ marginTop: 0 }}>Your VPN device</h2>
        {state?.peers?.length ? state.peers.map(peer => <div key={peer.id} style={{ padding: '12px 0', borderTop: '1px solid #e2e8f0' }}><strong>{peer.name}</strong><div style={{ color: '#64748b', fontSize: 14 }}>Address: {peer.address}</div><button disabled={working} onClick={() => remove(peer.id)} style={{ marginTop: 10, padding: '8px 12px', borderRadius: 8, border: '1px solid #fecaca', background: 'white', color: '#b91c1c' }}>Remove device</button></div>) : <p style={{ color: '#64748b' }}>No VPN device is provisioned for this account.</p>}
        {!state?.peers?.length && <><label htmlFor="vpn-device"><strong>Device name</strong></label><input id="vpn-device" value={device} onChange={e => setDevice(e.target.value)} placeholder="My Windows PC" maxLength={60} style={{ display: 'block', width: '100%', boxSizing: 'border-box', marginTop: 8, padding: 11, border: '1px solid #cbd5e1', borderRadius: 9 }} /><button disabled={working || !device.trim()} onClick={provision} style={{ marginTop: 12, padding: '10px 16px', border: 0, borderRadius: 9, background: '#0369a1', color: 'white', fontWeight: 700 }}>{working ? 'Provisioning…' : 'Create VPN configuration'}</button></>}
      </section>
      <section style={card}>
        <h2 style={{ marginTop: 0 }}>Connection details</h2>
        <p><strong>Protocol:</strong> WireGuard</p><p><strong>Server:</strong> {state?.endpoint || 'vpn.shopnoltd.dpdns.org:51820'}</p><p><strong>DNS:</strong> {state?.dns || '1.1.1.1'}</p>
        <h3>How to connect</h3><ol style={{ lineHeight: 1.8, paddingLeft: 22 }}><li>Install the official WireGuard client for your device.</li><li>Create your Shopnoltd VPN configuration here.</li><li>Download the configuration below and import it into WireGuard.</li><li>Activate the tunnel and verify that the connection is working.</li></ol>
        <p style={{ color: '#64748b', fontSize: 13 }}>The VPN private key is generated for your device and is only returned when the configuration is created.</p>
      </section>
    </div>}
    {result?.config && <section style={{ ...card, marginTop: 18, borderColor: '#86efac', background: '#f0fdf4' }}>
      <h2 style={{ marginTop: 0 }}>Configuration ready</h2><p>Your WireGuard configuration was created for <strong>{result.name}</strong>. Download it now; the private key is not stored by the browser.</p>
      <button onClick={() => downloadConfig(result.config, `${result.name.replace(/[^a-z0-9_-]+/gi,'-')}.conf`)} style={{ padding: '11px 16px', border: 0, borderRadius: 9, background: '#166534', color: 'white', fontWeight: 700 }}>Download WireGuard configuration</button>
    </section>}
    <p style={{ marginTop: 24, color: '#64748b', fontSize: 14 }}>Need help? Return to <Link to="/services">Shopnoltd Services</Link>.</p>
  </main>
}
