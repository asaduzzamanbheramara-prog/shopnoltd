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
  const [pendingSelection, setPendingSelection] = useState(null)
  const [selectedOAuthAccounts, setSelectedOAuthAccounts] = useState([])
  const [form, setForm] = useState(EMPTY)
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [automationPlatform, setAutomationPlatform] = useState('')
  const [automationAction, setAutomationAction] = useState('')
  const [automationSelected, setAutomationSelected] = useState([])
  const [automationPayload, setAutomationPayload] = useState('{}')
  const [automationApproved, setAutomationApproved] = useState(false)
  const [automationResults, setAutomationResults] = useState([])

  async function beginOAuth(provider, platform) {
    setError('')
    setBusy(true)
    try {
      const result = await platformApi.omnichannelOAuthAuthorizeUrl(provider, platform)
      if (!result?.authorization_url || !/^https:\/\//i.test(result.authorization_url)) {
        throw new Error('The provider did not return a valid authorization URL.')
      }
      window.location.assign(result.authorization_url)
    } catch (e) {
      setError(e.message || 'Could not start provider authorization.')
      setBusy(false)
    }
  }

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

  useEffect(() => {
    const query = new URLSearchParams(window.location.search)
    const oauthResult = query.get('oauth')
    const provider = query.get('provider')
    const reason = query.get('reason')
    const pendingId = query.get('pending_id')
    if (oauthResult) {
      query.delete('oauth')
      query.delete('provider')
      query.delete('connection_id')
      query.delete('reason')
      if (oauthResult !== 'pending') query.delete('pending_id')
      const remaining = query.toString()
      window.history.replaceState({}, '', `${window.location.pathname}${remaining ? `?${remaining}` : ''}`)
    }
    load().then(async () => {
      if (pendingId) {
        try {
          const pending = await platformApi.omnichannelOAuthPending(pendingId)
          setPendingSelection({ ...pending, pendingId })
          setSelectedOAuthAccounts((pending.choices || []).map(choice => choice.id))
        } catch (e) {
          setError(e.message || 'The account selection expired. Please reconnect the provider.')
        }
      }
      if (oauthResult === 'success') setNotice(`${provider || 'Provider'} account connected successfully.`)
      if (oauthResult === 'error') {
        const messages = {
          access_denied: 'You cancelled the provider authorization.',
          temporarily_unavailable: 'The provider is temporarily unavailable. Please try again.',
          server_error: 'The provider could not complete authorization. Please try again.',
          multiple_accounts: 'This login has multiple Pages or channels. Account selection is required; no account was connected.',
          no_eligible_account: 'No eligible Page, channel, or professional account was found. Check provider permissions and account type.',
        }
        setError(messages[reason] || 'Provider authorization failed. Check the provider app permissions and try again.')
      }
    })
  }, [])

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

  async function chooseOAuthAccounts(accountIds = selectedOAuthAccounts) {
    if (!pendingSelection?.pendingId || !accountIds.length) return
    setBusy(true)
    setError('')
    try {
      const result = await platformApi.omnichannelOAuthSelect(pendingSelection.pendingId, accountIds)
      setPendingSelection(null)
      setSelectedOAuthAccounts([])
      const currentQuery = new URLSearchParams(window.location.search)
      currentQuery.delete('pending_id')
      const remaining = currentQuery.toString()
      window.history.replaceState({}, '', window.location.pathname + (remaining ? '?' + remaining : ''))
      setNotice((result.connected_count || accountIds.length) + ' ' + result.platform + ' profile(s) connected successfully.')
      await load()
    } catch (e) {
      setError(e.message || 'Could not connect the selected accounts.')
    } finally {
      setBusy(false)
    }
  }

  function toggleOAuthAccount(accountId, checked) {
    setSelectedOAuthAccounts(current => checked
      ? [...new Set([...current, accountId])]
      : current.filter(id => id !== accountId))
  }

  const EXECUTABLE_ACTIONS = {
    gmail: ['send_message'],
    outlook: ['send_message'],
    x: ['create_post'],
    linkedin: ['create_post'],
  }
  const automationProfiles = items.filter(item => item.platform === automationPlatform && item.status === 'connected')
  const executableActions = EXECUTABLE_ACTIONS[automationPlatform] || []
  async function runAutomation(event) {
    event.preventDefault()
    setError('')
    setNotice('')
    setAutomationResults([])
    if (!automationSelected.length) { setError('Select at least one connected profile.'); return }
    if (!automationApproved) { setError('Explicit human approval is required before queuing provider actions.'); return }
    let payload
    try { payload = JSON.parse(automationPayload || '{}') } catch { setError('Action payload must be valid JSON.'); return }
    if (!payload || Array.isArray(payload) || typeof payload !== 'object') { setError('Action payload must be a JSON object.'); return }
    setBusy(true)
    const results = []
    try {
      for (const connectionId of automationSelected) {
        try {
          const result = await platformApi.omnichannelQueueAction({
            platform: automationPlatform,
            action: automationAction,
            connection_id: connectionId,
            idempotency_key: 'ui-' + crypto.randomUUID(),
            payload,
            approved: true,
          })
          results.push({ connectionId, ok: true, result })
        } catch (e) {
          results.push({ connectionId, ok: false, error: e.message })
        }
      }
      setAutomationResults(results)
      const queued = results.filter(x => x.ok).length
      setNotice(queued + ' of ' + results.length + ' action(s) queued. Queueing is not proof of provider delivery.')
    } finally {
      setBusy(false)
    }
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
              <span style={{ fontSize: 12, fontWeight: 700, color: ['ready_to_authorize', 'bot_configured'].includes(provider.setup_status) ? '#166534' : '#92400e' }}>
                {provider.setup_status === 'ready_to_authorize' ? 'Ready to authorize'
                  : provider.setup_status === 'bot_configured' ? 'Bot configured'
                  : provider.setup_status === 'business_onboarding_required' ? 'Business onboarding required'
                  : provider.setup_status === 'api_config_present_adapter_unverified' ? 'API details present — validation needed'
                  : 'Needs configuration'}
              </span>
            </div>
            <div style={{ color: '#6b7280', fontSize: 12, marginTop: 5 }}>
              {provider.platforms.join(', ')} · {provider.mode || 'oauth2'}
            </div>
            <div style={{ color: '#6b7280', fontSize: 11, marginTop: 5 }}>
              {provider.setup_status ? provider.setup_status.replaceAll('_', ' ') + '. ' : ''}
              {provider.authorization_supported ? 'Direct authorization is available when the server credentials are configured.' : 'Uses provider-specific business/API authorization.'}
            </div>
          </div>
        ))}
      </div>
    </section>

    {pendingSelection && <section style={{ ...styles.card, marginBottom: 20 }} aria-live="polite">
      <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>Choose profiles to connect</h2>
      <p style={{ margin: '0 0 12px', color: '#6b7280' }}>
        Select one, several, or all discovered {pendingSelection.platform} profiles from {pendingSelection.provider}. Each selected profile is saved as its own connection with separate account identity and credentials.
      </p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
        <button type="button" disabled={busy} onClick={() => setSelectedOAuthAccounts(pendingSelection.choices.map(choice => choice.id))} style={styles.button}>Select all ({pendingSelection.choices.length})</button>
        <button type="button" disabled={busy} onClick={() => setSelectedOAuthAccounts([])} style={styles.button}>Clear selection</button>
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {pendingSelection.choices.map(choice => <label
          key={choice.id}
          style={{ ...styles.button, justifyContent: 'flex-start', width: '100%', boxSizing: 'border-box', cursor: busy ? 'default' : 'pointer' }}
        >
          <input type="checkbox" disabled={busy} checked={selectedOAuthAccounts.includes(choice.id)} onChange={event => toggleOAuthAccount(choice.id, event.target.checked)} />
          <span>{choice.name}{choice.username ? ' (@' + choice.username + ')' : ''}</span>
        </label>)}
      </div>
      <button type="button" disabled={busy || !selectedOAuthAccounts.length} onClick={() => chooseOAuthAccounts()} style={{ ...styles.button, marginTop: 12, background: '#111827', color: '#fff', borderColor: '#111827' }}>
        {busy ? 'Connecting...' : 'Connect ' + selectedOAuthAccounts.length + ' selected profile(s)'}
      </button>
    </section>}

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
            {provider.platforms.map(platform => {
              const connectedCount = oauthProfiles.filter(x => x.provider === provider.provider && x.platform === platform).length
              return provider.configured && provider.authorization_supported
                ? <button key={platform} type="button" onClick={() => beginOAuth(provider.provider, platform)} disabled={busy} style={styles.button}>
                    <Link2 size={14} /> {connectedCount ? 'Connect another ' + platform + ' account' : 'Connect ' + platform}
                  </button>
                : <span key={platform} style={{ ...styles.button, color: '#92400e', cursor: 'default' }}>
                    {provider.mode === 'oauth2' ? 'Configure ' : 'Manual/API '} {platform}
                  </span>
            })}
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

    <section style={{ ...styles.card, marginBottom: 20 }}>
      <h2 style={{ margin: '0 0 8px', fontSize: 18 }}>One-command automation</h2>
      <p style={{ margin: '0 0 12px', color: '#6b7280', lineHeight: 1.5 }}>
        Select one platform and one or more of your connected profiles. Each action is queued against its own connection; credentials are never substituted across profiles.
      </p>
      <form onSubmit={runAutomation} style={{ display: 'grid', gap: 10 }}>
        <label>Platform
          <select value={automationPlatform} onChange={e => { setAutomationPlatform(e.target.value); setAutomationAction(''); setAutomationSelected([]); setAutomationResults([]) }} style={styles.input}>
            <option value="">Choose a platform</option>
            {Object.keys(EXECUTABLE_ACTIONS).map(platform => <option key={platform} value={platform}>{platform}</option>)}
          </select>
        </label>
        <label>Action
          <select value={automationAction} onChange={e => setAutomationAction(e.target.value)} style={styles.input} disabled={!executableActions.length}>
            <option value="">Choose an executable action</option>
            {executableActions.map(action => <option key={action} value={action}>{action}</option>)}
          </select>
        </label>
        <div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
            <strong>Target profiles ({automationSelected.length} selected)</strong>
            <button type="button" style={styles.button} disabled={!automationProfiles.length || busy} onClick={() => setAutomationSelected(automationProfiles.map(x => x.id))}>Select all</button>
            <button type="button" style={styles.button} disabled={busy} onClick={() => setAutomationSelected([])}>Clear</button>
          </div>
          {automationProfiles.length ? automationProfiles.map(item => <label key={item.id} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: 7, border: '1px solid #e5e7eb', borderRadius: 8, marginBottom: 6 }}>
            <input type="checkbox" checked={automationSelected.includes(item.id)} onChange={e => setAutomationSelected(current => e.target.checked ? [...new Set([...current, item.id])] : current.filter(id => id !== item.id))} />
            {item.display_name || item.username || item.platform_account_id} · {item.account_type}
          </label>) : <div style={{ color: '#92400e', fontSize: 13 }}>No connected profiles for this platform. Connect an account first.</div>}
        </div>
        <label>Action payload (JSON)
          <textarea rows={4} value={automationPayload} onChange={e => setAutomationPayload(e.target.value)} style={{ ...styles.input, fontFamily: 'monospace' }} placeholder='{"text":"Your approved message or post content"}' />
        </label>
        <label style={{ display: 'flex', gap: 8, alignItems: 'start' }}>
          <input type="checkbox" checked={automationApproved} onChange={e => setAutomationApproved(e.target.checked)} />
          I reviewed the selected profiles and payload, and explicitly approve this external action for each selected account.
        </label>
        <button type="submit" disabled={busy || !automationPlatform || !automationAction || !automationSelected.length || !automationApproved} style={{ ...styles.button, background: '#111827', color: '#fff', borderColor: '#111827', justifyContent: 'center' }}>
          {busy ? 'Queueing actions…' : 'Run on ' + automationSelected.length + ' selected profile(s)'}
        </button>
      </form>
      {automationResults.length > 0 && <div role="status" style={{ marginTop: 12, display: 'grid', gap: 6 }}>
        <strong>Queue results</strong>
        {automationResults.map(item => <div key={item.connectionId} style={{ fontSize: 12, color: item.ok ? '#166534' : '#991b1b' }}>
          {item.connectionId}: {item.ok ? 'queued (' + (item.result?.id || item.result?.status || 'accepted') + ')' : item.error}
        </div>)}
      </div>}
      <div style={{ color: '#92400e', fontSize: 12, marginTop: 10 }}>
        Currently wired only for Gmail/Outlook send_message and X/LinkedIn create_post. Other platforms remain unavailable until their provider adapters are implemented and verified. Country, provider policy, app review and IP restrictions still apply.
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
