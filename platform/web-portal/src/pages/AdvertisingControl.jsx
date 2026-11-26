import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { invalidateAdPolicyCache } from '../lib/useExternalAdPolicy'
import { tryRefresh } from '../lib/tokenRefresh'

const API = 'https://api.shopnoltd.dpdns.org/api/v1/ads'
const NETWORKS = [
  ['adsense', 'Google AdSense'],
  ['adsterra', 'Adsterra'],
  ['profiton', 'ProfitOn'],
  ['monetag', 'Monetag (approved host only)'],
]
const PLACEMENTS = [
  ['home', 'Home'],
  ['services', 'Services'],
  ['blog', 'Blog + articles'],
  ['feed', 'Social Feed'],
  ['downloads', 'Downloads'],
]
const EMPTY = {
  enabled: false,
  networks: { adsense: false, adsterra: false, monetag: false, profiton: false },
  placements: { home: false, services: false, blog: false, feed: false, downloads: false },
}
const panel = { background: '#fff', border: '1px solid #dbe3ee', borderRadius: 14, padding: 18 }
const button = { border: 0, borderRadius: 8, padding: '10px 14px', background: '#0369a1', color: '#fff', fontWeight: 700, cursor: 'pointer' }

async function api(path, options = {}) {
  const run = accessToken => fetch(API + path, {
    ...options,
    headers: {
      Accept: 'application/json',
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(accessToken ? { Authorization: 'Bearer ' + accessToken } : {}),
      ...(options.headers || {}),
    },
  })
  let response = await run(localStorage.getItem('shopno_token') || '')
  if (response.status === 401) {
    const refreshed = await tryRefresh()
    if (refreshed) response = await run(refreshed)
    else throw new Error('Your admin session expired. Sign in again.')
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || 'Advertising request failed (' + response.status + ')')
  return body
}

function normalizeHost(value) {
  return value.trim().toLowerCase().replace(/\.$/, '')
}

export default function AdvertisingControl() {
  const [policies, setPolicies] = useState([])
  const [selectedHost, setSelectedHost] = useState('')
  const [draft, setDraft] = useState(EMPTY)
  const [newHost, setNewHost] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const selected = useMemo(() => policies.find(item => item.hostname === selectedHost), [policies, selectedHost])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const rows = await api('/admin/external-policies')
      setPolicies(Array.isArray(rows) ? rows : [])
      if (!selectedHost && rows.length) setSelectedHost(rows[0].hostname)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [selectedHost])

  useEffect(() => { refresh() }, [refresh])

  useEffect(() => {
    if (selected) {
      setDraft({
        enabled: Boolean(selected.enabled),
        networks: { ...EMPTY.networks, ...(selected.networks || {}) },
        placements: { ...EMPTY.placements, ...(selected.placements || {}) },
      })
    } else {
      setDraft(EMPTY)
    }
  }, [selected])

  function toggle(group, key, value) {
    setDraft(current => ({ ...current, [group]: { ...current[group], [key]: value } }))
  }

  async function save(host = selectedHost, value = draft) {
    if (!host) return
    setSaving(true); setError(''); setMessage('')
    try {
      const result = await api('/admin/external-policies/' + encodeURIComponent(host), {
        method: 'PUT',
        body: JSON.stringify(value),
      })
      setPolicies(current => [...current.filter(item => item.hostname !== result.hostname), result].sort((a, b) => a.hostname.localeCompare(b.hostname)))
      setSelectedHost(result.hostname)
      invalidateAdPolicyCache(result.hostname)
      setMessage('Advertising policy saved for ' + result.hostname + '. New settings apply on the next page load.')
    } catch (e) {
      setError(e.message)
    } finally {
      setSaving(false)
    }
  }

  async function addHost(event) {
    event.preventDefault()
    const host = normalizeHost(newHost)
    if (!host) return
    const exists = policies.some(item => item.hostname === host)
    if (exists) {
      setSelectedHost(host)
      setNewHost('')
      return
    }
    const value = {
      enabled: false,
      networks: { ...EMPTY.networks },
      placements: { ...EMPTY.placements },
    }
    await save(host, value)
    setNewHost('')
  }

  return <main style={{ maxWidth: 1120, margin: '0 auto', padding: '34px 18px 80px', minHeight: '75vh', background: '#f8fafc' }}>
    <header style={{ marginBottom: 22 }}>
      <div style={{ color: '#0369a1', fontSize: 12, fontWeight: 800, letterSpacing: '.08em' }}>PLATFORM ADMIN · ADVERTISING</div>
      <h1 style={{ margin: '6px 0' }}>Advertising Command Center</h1>
      <p style={{ color: '#475569', lineHeight: 1.6, maxWidth: 850 }}>
        Control Google AdSense, Adsterra, Monetag and ProfitOn separately for each exact domain or subdomain. New hosts start disabled. Shopnoltd subdomains are covered by the central API; custom domains also need their exact HTTPS origin added to the API service CORS_ORIGINS allowlist and this policy hook integrated into that site's frontend. Only enable a provider after that exact host is approved in its publisher dashboard.
      </p>
    </header>

    {message && <p role="status" style={{ ...panel, color: '#166534' }}>{message}</p>}
    {error && <p role="alert" style={{ ...panel, color: '#991b1b' }}>{error}</p>}

    <section style={{ ...panel, marginBottom: 18 }}>
      <h2 style={{ marginTop: 0 }}>Add domain or subdomain</h2>
      <form onSubmit={addHost} style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        <input value={newHost} onChange={e => setNewHost(e.target.value)} placeholder="social.shopnoltd.dpdns.org" aria-label="Domain or subdomain" required style={{ flex: '1 1 260px', minWidth: 0, padding: 11, border: '1px solid #cbd5e1', borderRadius: 8 }} />
        <button type="submit" disabled={saving} style={button}>Add host (starts OFF)</button>
      </form>
      <p style={{ color: '#64748b', fontSize: 13, marginBottom: 0 }}>Exact hostname matching only—no wildcard. Add each approved subdomain separately so an unapproved service cannot inherit ads accidentally.</p>
    </section>

    <section style={{ ...panel, marginBottom: 18 }}>
      <h2 style={{ marginTop: 0 }}>Configured hosts</h2>
      {loading ? <p>Loading host policies…</p> : policies.length === 0 ? <p>No host policies found. Add the first approved domain above.</p> :
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {policies.map(item => <button key={item.hostname} type="button" onClick={() => setSelectedHost(item.hostname)} style={{ border: selectedHost === item.hostname ? '2px solid #0284c7' : '1px solid #cbd5e1', background: selectedHost === item.hostname ? '#e0f2fe' : '#fff', color: '#0f172a', borderRadius: 8, padding: '9px 12px', cursor: 'pointer' }}>{item.hostname} · {item.enabled ? 'ON' : 'OFF'}</button>)}
        </div>}
    </section>

    {selectedHost && <section style={panel}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <div><h2 style={{ margin: 0 }}>{selectedHost}</h2><p style={{ color: '#64748b', margin: '5px 0 0' }}>Host-wide master switch</p></div>
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: 9, fontWeight: 800 }}>
          <input type="checkbox" checked={draft.enabled} onChange={e => setDraft(current => ({ ...current, enabled: e.target.checked }))} />
          Advertising {draft.enabled ? 'ON' : 'OFF'}
        </label>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 16, marginTop: 20 }}>
        <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 14 }}>
          <h3 style={{ marginTop: 0 }}>Ad networks</h3>
          {NETWORKS.map(([key, label]) => <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '12px 0' }}>
            <input type="checkbox" checked={draft.networks[key]} disabled={key === 'profiton' && selectedHost !== 'shopnoltd.dpdns.org'} onChange={e => toggle('networks', key, e.target.checked)} />
            <span>{label}{key === 'monetag' ? ' — requires exact-host publisher approval and MONETAG_APPROVED_HOSTS allowlist' : key === 'profiton' && selectedHost !== 'shopnoltd.dpdns.org' ? ' — apex host only until vendor approval' : ''}</span>
          </label>)}
        </div>
        <div style={{ border: '1px solid #e2e8f0', borderRadius: 10, padding: 14 }}>
          <h3 style={{ marginTop: 0 }}>Ad placements</h3>
          {PLACEMENTS.map(([key, label]) => <label key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '12px 0' }}>
            <input type="checkbox" checked={draft.placements[key]} onChange={e => toggle('placements', key, e.target.checked)} />
            <span>{label}</span>
          </label>)}
        </div>
      </div>
      <p style={{ color: '#92400e', background: '#fffbeb', borderRadius: 8, padding: 12, lineHeight: 1.5 }}>
        Login, registration, admin, dashboard, wallet, payment, checkout and account routes are always excluded in code. Consent is still required before optional ad scripts load. Monetag can be enabled only for exact hostnames listed in the ad-service MONETAG_APPROVED_HOSTS deployment setting after publisher approval and the content-host browser test. ProfitOn is restricted to the apex host; its Smartlink 162185 is a user-click link. Shuffle Box 162186 and Pops 162184 remain off until the exact vendor code and SPA cleanup are verified. AdSense currently has a publisher loader but no explicit ad-unit slot ID in this repository.
      </p>
      <button type="button" disabled={saving || !selected} onClick={() => save()} style={button}>{saving ? 'Saving…' : 'Save advertising settings'}</button>
    </section>}
  </main>
}
