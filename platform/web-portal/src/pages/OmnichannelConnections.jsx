import { useEffect, useMemo, useState } from 'react'
import { ArrowLeft, CheckCircle2, Link2, Pencil, Plus, RefreshCw, Trash2, XCircle } from 'lucide-react'
import { Link } from 'react-router-dom'
import { platformApi } from '../lib/platformApi'

const PLATFORMS = ['whatsapp', 'facebook', 'instagram', 'linkedin', 'x', 'telegram', 'tiktok', 'youtube', 'gmail', 'outlook', '3cx']

const EMPTY = {
  platform: 'whatsapp',
  account_type: 'user',
  platform_account_id: '',
  username: '',
  display_name: '',
  status: 'connected',
  scopes: '',
  access_token_ref: '',
  refresh_token_ref: '',
  token_expires_at: '',
  metadata: '',
}

const styles = {
  page: { maxWidth: 1120, margin: '0 auto', padding: 24 },
  card: { border: '1px solid #e5e7eb', borderRadius: 14, padding: 18, background: '#fff' },
  input: { width: '100%', boxSizing: 'border-box', padding: 9, border: '1px solid #d1d5db', borderRadius: 8 },
  button: { border: '1px solid #d1d5db', borderRadius: 8, padding: '8px 11px', background: '#fff', cursor: 'pointer', display: 'inline-flex', gap: 6, alignItems: 'center' },
}

function toPayload(form) {
  let metadata = {}
  if (form.metadata.trim()) metadata = JSON.parse(form.metadata)
  return {
    platform: form.platform,
    account_type: form.account_type || 'user',
    platform_account_id: form.platform_account_id.trim(),
    username: form.username.trim() || null,
    display_name: form.display_name.trim() || null,
    status: form.status || 'connected',
    scopes: form.scopes.split(',').map(x => x.trim()).filter(Boolean),
    access_token_ref: form.access_token_ref.trim() || null,
    refresh_token_ref: form.refresh_token_ref.trim() || null,
    token_expires_at: form.token_expires_at || null,
    metadata,
  }
}

function fromConnection(item) {
  return {
    platform: item.platform || 'whatsapp',
    account_type: item.account_type || 'user',
    platform_account_id: item.platform_account_id || '',
    username: item.username || '',
    display_name: item.display_name || '',
    status: item.status || 'connected',
    scopes: Array.isArray(item.scopes) ? item.scopes.join(', ') : '',
    access_token_ref: item.access_token_ref || '',
    refresh_token_ref: item.refresh_token_ref || '',
    token_expires_at: item.token_expires_at ? String(item.token_expires_at).slice(0, 16) : '',
    metadata: item.metadata ? JSON.stringify(item.metadata, null, 2) : '',
  }
}

export default function OmnichannelConnections() {
  const [items, setItems] = useState([])
  const [capabilities, setCapabilities] = useState([])
  const [providers, setProviders] = useState([])
  const [oauthProfiles, setOauthProfiles] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function load() {
    setError('')
    try {
      const [connections, caps, providerStatus, oauthProfilesResult] = await Promise.all([
        platformApi.omnichannelConnections(),
        platformApi.omnichannelCapabilities(),
        platformApi.omnichannelProviders(),
        platformApi.omnichannelOAuthStatus(),
      ])
      setItems(Array.isArray(connections) ? connections : [])
      setCapabilities(Array.isArray(caps) ? caps : [])
      setProviders(Array.isArray(providerStatus) ? providerStatus : [])
      setOauthProfiles(Array.isArray(oauthProfilesResult) ? oauthProfilesResult : [])
    } catch (e) {
      setError(e.message)
    }
  }

  useEffect(() => { load() }, [])

  const capabilityMap = useMemo(() => {
    const map = {}
    for (const item of capabilities) {
      if (!map[item.platform]) map[item.platform] = []
      map[item.platform].push(item)
    }
    return map
  }, [capabilities])

  function update(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  function resetForm() {
    setForm(EMPTY)
    setEditing(null)
  }

  async function save(event) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const payload = toPayload(form)
      if (!payload.platform_account_id) throw new Error('Platform account ID is required')
      if (editing) {
        await platformApi.updateOmnichannelConnection(editing, payload)
        setNotice('Platform profile updated.')
      } else {
        await platformApi.addOmnichannelConnection(payload)
        setNotice('Platform profile registered.')
      }
      resetForm()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  function edit(item) {
    setEditing(item.id)
    setForm(fromConnection(item))
    setError('')
    setNotice('')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  async function remove(item) {
    if (!window.confirm(`Disconnect ${item.display_name || item.username || item.platform_account_id} from Shopnoltd?`)) return
    setBusy(true)
    setError('')
    try {
      await platformApi.deleteOmnichannelConnection(item.id)
      setNotice('Platform profile disconnected.')
      if (editing === item.id) resetForm()
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  return <main style={styles.page}>
    <Link to="/dashboard" style={{ display: 'inline-flex', gap: 6, alignItems: 'center', color: '#374151', textDecoration: 'none', marginBottom: 18 }}>
      <ArrowLeft size={16} /> Back to Dashboard
    </Link>

    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'start', marginBottom: 18 }}>
      <div>
        <h1 style={{ margin: 0 }}>Platform Accounts & Profiles</h1>
        <p style={{ margin: '7px 0 0', color: '#6b7280', lineHeight: 1.55 }}>
          Manage your Shopnoltd connections across WhatsApp, Facebook, Instagram, LinkedIn, X, Telegram, TikTok, YouTube, Gmail, Outlook and 3CX.
        </p>
      </div>
      <button type="button" onClick={load} disabled={busy} style={styles.button}><RefreshCw size={15} /> Refresh</button>
    </div>

    {error && <div role="alert" style={{ padding: 11, marginBottom: 12, borderRadius: 9, background: '#fef2f2', color: '#991b1b' }}><XCircle size={15} style={{ verticalAlign: 'middle', marginRight: 5 }} />{error}</div>}
    {notice && <div role="status" style={{ padding: 11, marginBottom: 12, borderRadius: 9, background: '#f0fdf4', color: '#166534' }}><CheckCircle2 size={15} style={{ verticalAlign: 'middle', marginRight: 5 }} />{notice}</div>}

    <form onSubmit={save} style={{ ...styles.card, display: 'grid', gap: 10, marginBottom: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>{editing ? 'Edit platform profile' : 'Register platform profile'}</h2>
        {editing && <button type="button" onClick={resetForm} style={styles.button}><XCircle size={14} /> Cancel</button>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(180px,1fr))', gap: 10 }}>
        <label>Platform<select value={form.platform} onChange={e => update('platform', e.target.value)} style={styles.input} disabled={!!editing}>{PLATFORMS.map(x => <option key={x}>{x}</option>)}</select></label>
        <label>Account type<input value={form.account_type} onChange={e => update('account_type', e.target.value)} placeholder="user / page / business / channel" style={styles.input} /></label>
        <label>Platform account ID<input required value={form.platform_account_id} onChange={e => update('platform_account_id', e.target.value)} style={styles.input} /></label>
        <label>Username<input value={form.username} onChange={e => update('username', e.target.value)} style={styles.input} /></label>
        <label>Display name<input value={form.display_name} onChange={e => update('display_name', e.target.value)} style={styles.input} /></label>
        <label>Status<select value={form.status} onChange={e => update('status', e.target.value)} style={styles.input}><option>connected</option><option>pending</option><option>expired</option><option>disabled</option></select></label>
      </div>

      <label>Scopes <input value={form.scopes} onChange={e => update('scopes', e.target.value)} placeholder="scope.one, scope.two" style={styles.input} /></label>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 10 }}>
        <label>Access credential reference <input value={form.access_token_ref} onChange={e => update('access_token_ref', e.target.value)} placeholder="Secret-manager reference only; do not paste a token" style={styles.input} /></label>
        <label>Refresh credential reference <input value={form.refresh_token_ref} onChange={e => update('refresh_token_ref', e.target.value)} placeholder="Secret-manager reference only; do not paste a token" style={styles.input} /></label>
        <label>Token expiry <input type="datetime-local" value={form.token_expires_at} onChange={e => update('token_expires_at', e.target.value)} style={styles.input} /></label>
      </div>
      <label>Metadata JSON <textarea rows={4} value={form.metadata} onChange={e => update('metadata', e.target.value)} placeholder='{"profile_url":"https://..."}' style={{ ...styles.input, fontFamily: 'monospace' }} /></label>

      <div style={{ display: 'flex', gap: 8 }}>
        <button disabled={busy} style={{ ...styles.button, background: '#111827', color: '#fff', borderColor: '#111827' }}>
          {editing ? <Pencil size={14} /> : <Plus size={14} />}{busy ? 'Saving…' : editing ? 'Update profile' : 'Register profile'}
        </button>
      </div>
      <div style={{ color: '#6b7280', fontSize: 12 }}>
        Use provider authorization above for supported OAuth platforms. Manual registration remains available for provider-specific integrations such as WhatsApp, Telegram and 3CX.
      </div>
    </form>


    <section style={{ ...styles.card, marginBottom: 20 }}>
      <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Direct provider connection readiness</h2>
      <p style={{ margin: '0 0 12px', color: '#6b7280', lineHeight: 1.5 }}>
        Shopnoltd now checks which provider integrations are configured by the server. OAuth client secrets are never exposed to the browser.
        A provider marked <strong>Not configured</strong> requires its developer application credentials to be installed in the cluster secret manager before a direct authorization button can safely be enabled.
      </p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(230px,1fr))', gap: 10 }}>
        {providers.map(provider => (
          <div key={provider.provider} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 11 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <strong>{provider.provider}</strong>
              <span style={{ fontSize: 12, fontWeight: 700, color: provider.configured ? '#166534' : '#92400e' }}>
                {provider.configured ? 'Configured' : 'Not configured'}
              </span>
            </div>
            <div style={{ color: '#6b7280', fontSize: 12, marginTop: 5 }}>
              {provider.platforms.join(', ')} · {provider.mode || 'oauth2'}
            </div>
            <div style={{ color: '#6b7280', fontSize: 11, marginTop: 5 }}>
              {provider.authorization_supported ? 'Direct authorization is available when the server credentials are configured.' : 'Uses provider-specific business/API authorization.'}
            </div>
          </div>
        ))}
      </div>
    </section>

    <section style={{ ...styles.card, marginBottom: 20 }}>
      <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Authorize provider accounts</h2>
      <p style={{ margin: '0 0 12px', color: '#6b7280', lineHeight: 1.5 }}>
        Use the provider authorization button to connect an account. Shopnoltd stores encrypted provider tokens server-side and exposes only the connection/profile reference to automation.
      </p>
      {providers.map(provider => (
        <div key={provider.provider} style={{ borderTop: '1px solid #e5e7eb', padding: '12px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'center' }}>
            <strong>{provider.provider}</strong>
            <span style={{ fontSize: 12, color: '#6b7280' }}>
              {oauthProfiles.filter(x => x.provider === provider.provider).length} connected profile(s)
            </span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 9 }}>
            {provider.platforms.map(platform => (
              provider.configured && provider.authorization_supported
                ? <button key={platform} type="button" onClick={() => { window.location.href = platformApi.omnichannelOAuthStart(provider.provider, platform) }} style={styles.button}>
                    <Link2 size={14} /> Connect {platform}
                  </button>
                : <span key={platform} style={{ ...styles.button, color: '#92400e', cursor: 'default' }}>
                    {provider.mode === 'oauth2' ? 'Configure ' : 'Manual/API '} {platform}
                  </span>
            ))}
          </div>
        </div>
      ))}
    </section>

        <section style={{ ...styles.card, marginBottom: 20 }}>
      <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Platform capability matrix</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(190px,1fr))', gap: 10 }}>
        {PLATFORMS.map(platform => {
          const caps = capabilityMap[platform] || []
          return <div key={platform} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 11 }}>
            <strong>{platform}</strong>
            <div style={{ color: '#6b7280', fontSize: 12, marginTop: 5 }}>
              {caps.length ? caps.map(x => x.action).join(', ') : 'No capability records'}
            </div>
            {caps.some(x => x.availability === 'provider_dependent') && <div style={{ color: '#92400e', fontSize: 11, marginTop: 5 }}>Provider approval may be required</div>}
          </div>
        })}
      </div>
    </section>

    <section>
      <h2 style={{ margin: '0 0 12px', fontSize: 18 }}>Connected profiles ({items.length})</h2>
      <div style={{ display: 'grid', gap: 12 }}>
        {items.map(item => <article key={item.id} style={styles.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontWeight: 700 }}>
                <Link2 size={17} /> {item.platform} · {item.display_name || item.username || item.platform_account_id}
              </div>
              <div style={{ color: '#6b7280', fontSize: 12, marginTop: 5 }}>
                {item.account_type || 'user'} · ID {item.platform_account_id} · status: {item.status || 'unknown'}
              </div>
            </div>
            <div style={{ display: 'flex', gap: 7 }}>
              <button type="button" onClick={() => edit(item)} style={styles.button}><Pencil size={14} /> Edit</button>
              <button type="button" onClick={() => remove(item)} disabled={busy} style={{ ...styles.button, color: '#991b1b' }}><Trash2 size={14} /> Disconnect</button>
            </div>
          </div>
          <div style={{ marginTop: 10, fontSize: 12, color: '#4b5563' }}>
            Scopes: {Array.isArray(item.scopes) && item.scopes.length ? item.scopes.join(', ') : 'none recorded'}
          </div>
          {item.token_expires_at && <div style={{ marginTop: 4, fontSize: 12, color: '#4b5563' }}>Credential expiry: {item.token_expires_at}</div>}
        </article>)}
        {!items.length && <div style={{ ...styles.card, borderStyle: 'dashed', color: '#6b7280' }}>
          No platform profiles are connected for this account yet. Register one after completing the provider's authorization flow.
        </div>}
      </div>
    </section>
  </main>
}
