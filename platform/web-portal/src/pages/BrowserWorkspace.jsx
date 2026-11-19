import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bot, Globe, Lock, Plus, RefreshCw, ShieldCheck, X } from 'lucide-react'
import { tryRefresh } from '../lib/tokenRefresh'
import AgentWorkspace from './AgentWorkspace'

const SESSION_API = 'https://sessions.shopnoltd.dpdns.org'

function tokenExpiry(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return payload.exp * 1000 - Date.now()
  } catch {
    return 0
  }
}

async function accessToken() {
  let token = localStorage.getItem('shopno_token')
  if (!token || tokenExpiry(token) < 60000) {
    token = (await tryRefresh()) || localStorage.getItem('shopno_token')
  }
  return token && tokenExpiry(token) > 0 ? token : null
}

async function sessionRequest(path, options = {}) {
  const token = await accessToken()
  if (!token) throw new Error('Your Shopnoltd session expired. Sign in again.')
  const response = await fetch(`${SESSION_API}${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.headers || {}),
    },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status === 401) throw new Error('Session Manager rejected this token. Sign in again; if the issue continues, the Keycloak api-service audience needs verification.')
    throw new Error(payload.detail || `Browser request failed (HTTP ${response.status}).`)
  }
  return payload
}

const buttonStyle = { border: '1px solid #d1d5db', borderRadius: 9, padding: '8px 12px', background: '#fff', color: '#111827', cursor: 'pointer', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 7 }
const inputStyle = { minWidth: 0, width: '100%', border: '1px solid #cbd5e1', borderRadius: 9, padding: '10px 12px', font: 'inherit', boxSizing: 'border-box' }

export default function BrowserWorkspace() {
  const [profiles, setProfiles] = useState([])
  const [activeId, setActiveId] = useState('')
  const [targetUrl, setTargetUrl] = useState('https://shopnoltd.dpdns.org/')
  const [profileName, setProfileName] = useState('')
  const [purpose, setPurpose] = useState('qa')
  const [viewerUrl, setViewerUrl] = useState('')
  const [agentOpen, setAgentOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Loading your private browser profiles…')
  const [error, setError] = useState('')

  const activeProfile = useMemo(() => profiles.find((profile) => profile.id === activeId) || null, [profiles, activeId])

  const refreshProfiles = useCallback(async () => {
    const result = await sessionRequest('/api/profiles')
    setProfiles(Array.isArray(result) ? result : [])
    setActiveId((current) => current && result.some((profile) => profile.id === current) ? current : (result[0]?.id || ''))
    setStatus('Your browser profiles are isolated to your Shopnoltd account.')
  }, [])

  useEffect(() => {
    let mounted = true
    sessionRequest('/api/profiles')
      .then((result) => {
        if (!mounted) return
        setProfiles(Array.isArray(result) ? result : [])
        setActiveId(result[0]?.id || '')
        setStatus('Your browser profiles are isolated to your Shopnoltd account.')
      })
      .catch((err) => { if (mounted) { setError(err.message); setStatus('Browser service needs attention.') } })
    return () => { mounted = false }
  }, [])

  async function createProfile(event) {
    event.preventDefault()
    if (!profileName.trim()) return
    setBusy(true); setError('')
    try {
      const created = await sessionRequest('/api/profiles', {
        method: 'POST',
        body: JSON.stringify({ name: profileName.trim(), purpose }),
      })
      setProfiles((current) => [created, ...current])
      setActiveId(created.id)
      setProfileName('')
      setViewerUrl('')
      setStatus('Private browser profile created.')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function openBrowser(event) {
    event?.preventDefault()
    if (!activeProfile) { setError('Create or select a browser profile first.'); return }
    let url
    try {
      url = new URL(targetUrl.trim())
      if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password) throw new Error()
    } catch {
      setError('Enter a valid public http:// or https:// address.')
      return
    }
    setBusy(true); setError('')
    try {
      await sessionRequest('/api/sessions/launch', {
        method: 'POST',
        body: JSON.stringify({ profile_id: activeProfile.id, target_url: url.toString(), headless: false }),
      })
      const ticket = await sessionRequest(`/api/sessions/${activeProfile.id}/viewer-ticket`, { method: 'POST' })
      setViewerUrl(ticket.viewer_url)
      setStatus(`Connected to ${activeProfile.name}. Viewer authorization expires after 60 seconds; the live view cookie lasts 10 minutes.`)
    } catch (err) { setError(err.message); setStatus('Unable to start this browser session.') } finally { setBusy(false) }
  }

  async function closeBrowser() {
    if (!activeProfile) return
    setBusy(true); setError('')
    try {
      await sessionRequest(`/api/sessions/${activeProfile.id}/close`, { method: 'POST' })
      setViewerUrl('')
      setStatus('Browser session closed and viewer access revoked.')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  async function deleteProfile() {
    if (!activeProfile || !window.confirm(`Delete profile “${activeProfile.name}”? This does not delete other profiles.`)) return
    setBusy(true); setError('')
    try {
      await sessionRequest(`/api/profiles/${activeProfile.id}`, { method: 'DELETE' })
      setProfiles((current) => current.filter((profile) => profile.id !== activeProfile.id))
      setActiveId('')
      setViewerUrl('')
      setStatus('Profile deleted.')
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }

  return (
    <main style={{ height: 'calc(100vh - 70px)', minHeight: 540, display: 'flex', flexDirection: 'column', background: '#f8fafc', color: '#111827', overflow: 'hidden' }}>
      <header style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 18px', background: '#0f172a', color: '#fff', flexWrap: 'wrap' }}>
        <Globe size={20} />
        <strong style={{ fontSize: 18 }}>Shopnoltd Browser</strong>
        <span style={{ fontSize: 12, color: '#cbd5e1', display: 'inline-flex', alignItems: 'center', gap: 5 }}><ShieldCheck size={14} /> Isolated remote browser</span>
        <span style={{ flex: 1 }} />
        <button type="button" onClick={() => setAgentOpen((value) => !value)} style={{ ...buttonStyle, background: agentOpen ? '#0ea5e9' : '#fff', color: agentOpen ? '#fff' : '#111827' }}><Bot size={15} /> {agentOpen ? 'Hide Agent' : 'AI Agent'}</button>
      </header>

      <form onSubmit={openBrowser} style={{ display: 'flex', gap: 8, alignItems: 'center', padding: 12, background: '#fff', borderBottom: '1px solid #e2e8f0' }}>
        <Lock size={17} color="#64748b" />
        <input aria-label="Browser address" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="Enter a website address" style={inputStyle} />
        <button disabled={busy || !activeProfile} type="submit" style={{ ...buttonStyle, background: '#0ea5e9', color: '#fff', borderColor: '#0ea5e9', opacity: busy || !activeProfile ? .55 : 1 }}><Globe size={15} /> {busy ? 'Working…' : 'Go'}</button>
        <button disabled={busy || !viewerUrl} type="button" onClick={() => setViewerUrl((value) => value ? `${value.split('#')[0]}#${value.split('#')[1] || ''}` : '')} style={buttonStyle}><RefreshCw size={15} /> Refresh view</button>
        <button disabled={busy || !viewerUrl} type="button" onClick={closeBrowser} style={buttonStyle}><X size={15} /> Close</button>
      </form>

      <div style={{ display: 'grid', gridTemplateColumns: agentOpen ? '250px minmax(0,1fr) minmax(300px,380px)' : '250px minmax(0,1fr)', minHeight: 0, flex: 1 }}>
        <aside style={{ minWidth: 0, overflowY: 'auto', borderRight: '1px solid #e2e8f0', background: '#fff', padding: 14 }}>
          <div style={{ fontSize: 12, fontWeight: 800, color: '#64748b', letterSpacing: '.08em', textTransform: 'uppercase', marginBottom: 10 }}>Your profiles</div>
          <form onSubmit={createProfile} style={{ display: 'grid', gap: 8, marginBottom: 16 }}>
            <input value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="New profile name" aria-label="New profile name" style={inputStyle} />
            <select value={purpose} onChange={(event) => setPurpose(event.target.value)} style={inputStyle} aria-label="Profile purpose">
              <option value="qa">QA / personal</option>
              <option value="staff">Staff</option>
              <option value="scraping">Research / scraping</option>
            </select>
            <button disabled={busy || !profileName.trim()} type="submit" style={{ ...buttonStyle, justifyContent: 'center', opacity: busy || !profileName.trim() ? .55 : 1 }}><Plus size={15} /> Create profile</button>
          </form>
          <div style={{ display: 'grid', gap: 7 }}>
            {profiles.map((profile) => (
              <button key={profile.id} type="button" onClick={() => { setActiveId(profile.id); setViewerUrl('') }} style={{ textAlign: 'left', border: activeId === profile.id ? '2px solid #0ea5e9' : '1px solid #e2e8f0', borderRadius: 10, padding: 10, background: activeId === profile.id ? '#f0f9ff' : '#fff', cursor: 'pointer', color: '#0f172a' }}>
                <div style={{ fontWeight: 700, overflowWrap: 'anywhere' }}>{profile.name}</div>
                <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>{profile.purpose} · {profile.is_active ? 'Enabled' : 'Disabled'}</div>
              </button>
            ))}
            {!profiles.length && <p style={{ color: '#64748b', fontSize: 13 }}>No browser profiles yet.</p>}
          </div>
          {activeProfile && <button type="button" onClick={deleteProfile} disabled={busy} style={{ ...buttonStyle, width: '100%', justifyContent: 'center', marginTop: 14, color: '#b91c1c' }}>Delete selected profile</button>}
        </aside>

        <section style={{ minWidth: 0, minHeight: 0, display: 'flex', flexDirection: 'column', background: '#e2e8f0' }}>
          <div style={{ padding: '8px 14px', display: 'flex', gap: 8, alignItems: 'center', background: '#fff', borderBottom: '1px solid #e2e8f0', fontSize: 13 }}>
            <span style={{ fontWeight: 700 }}>{activeProfile?.name || 'No profile selected'}</span>
            <span style={{ color: '#64748b', flex: 1 }}>{status}</span>
          </div>
          {error && <div role="alert" style={{ padding: 10, color: '#991b1b', background: '#fef2f2', borderBottom: '1px solid #fecaca', fontSize: 13 }}>{error}</div>}
          {viewerUrl ? (
            <iframe key={viewerUrl} title="Shopnoltd remote browser" src={viewerUrl} referrerPolicy="no-referrer" allow="clipboard-read; clipboard-write; fullscreen" allowFullScreen style={{ flex: 1, width: '100%', minHeight: 0, border: 0, background: '#111827' }} />
          ) : (
            <div style={{ flex: 1, display: 'grid', placeItems: 'center', padding: 24, textAlign: 'center' }}>
              <div style={{ maxWidth: 460 }}>
                <div style={{ width: 60, height: 60, borderRadius: 18, margin: '0 auto 14px', display: 'grid', placeItems: 'center', background: '#0f172a', color: '#fff' }}><Globe size={28} /></div>
                <h1 style={{ margin: '0 0 8px', fontSize: 24 }}>Browse with Shopnoltd</h1>
                <p style={{ color: '#475569', lineHeight: 1.6 }}>Create or select a private profile, enter a website address, and press Go. Browser cookies and storage are isolated by profile.</p>
              </div>
            </div>
          )}
        </section>

        {agentOpen && <aside style={{ minWidth: 0, minHeight: 0, overflow: 'hidden', borderLeft: '1px solid #e2e8f0', background: '#fff' }}><AgentWorkspace /></aside>}
      </div>
    </main>
  )
}
