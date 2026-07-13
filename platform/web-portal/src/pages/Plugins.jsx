import { useEffect, useState } from 'react'

// Reads/writes Tenant.settings.plugins via
// GET/PATCH /api/v1/tenants/{tenant_id}/settings (see
// platform/oauth-service/app/api/tenant_settings.py). Read is public;
// writing requires a platform_admin or tenant_owner token.

const KNOWN_PLUGINS = [
  { key: 'blog', label: 'Blog', description: 'Public blog/content pages for this tenant.' },
  { key: 'live_chat', label: 'Live Chat', description: 'Chatwoot-powered customer chat widget.' },
  { key: 'surveys', label: 'Surveys', description: 'KoboToolbox-powered data collection forms.' },
  { key: 'meetings', label: 'Video Meetings', description: 'Jitsi-powered video conferencing.' },
]

export default function Plugins() {
  const [tenantId, setTenantId] = useState('')
  const [plugins, setPlugins] = useState({})
  const [status, setStatus] = useState('')

  async function load() {
    if (!tenantId) return
    setStatus('Loading…')
    try {
      const r = await fetch(`/api/v1/tenants/${tenantId}/settings`)
      const d = await r.json()
      setPlugins(d.plugins || {})
      setStatus('')
    } catch (e) {
      setStatus('Could not load settings: ' + e.message)
    }
  }

  async function toggle(key) {
    const token = localStorage.getItem('shopno_token')
    if (!token) { setStatus('Sign in as an admin or tenant owner to change plugins.'); return }
    const next = { ...plugins, [key]: !plugins[key] }
    setStatus('Saving…')
    try {
      const r = await fetch(`/api/v1/tenants/${tenantId}/settings`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ plugins: next }),
      })
      if (!r.ok) { setStatus(`Save failed (HTTP ${r.status}) -- do you have tenant_owner/platform_admin access?`); return }
      const d = await r.json()
      setPlugins(d.plugins || {})
      setStatus('Saved.')
    } catch (e) {
      setStatus('Save failed: ' + e.message)
    }
  }

  useEffect(() => { load() }, [tenantId])

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Plugins</h1>
      <p style={{ color: '#64748b' }}>Enable or disable optional modules for a tenant.</p>
      <input
        placeholder="Tenant ID"
        value={tenantId}
        onChange={e => setTenantId(e.target.value)}
        style={{ padding: 10, width: '100%', margin: '16px 0', boxSizing: 'border-box' }}
      />
      {status && <p style={{ color: '#0ea5e9' }}>{status}</p>}
      <div style={{ display: 'grid', gap: 12 }}>
        {KNOWN_PLUGINS.map(p => (
          <div key={p.key} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 16, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div>
              <strong>{p.label}</strong>
              <p style={{ color: '#64748b', margin: 0 }}>{p.description}</p>
            </div>
            <button
              onClick={() => toggle(p.key)}
              style={{ padding: '8px 16px', borderRadius: 8, border: 0, cursor: 'pointer', background: plugins[p.key] ? '#10b981' : '#e2e8f0', color: plugins[p.key] ? 'white' : '#334155' }}
            >
              {plugins[p.key] ? 'Enabled' : 'Disabled'}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
