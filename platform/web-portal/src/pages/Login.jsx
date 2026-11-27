import { useEffect, useRef, useState } from 'react'
import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI, SOCIAL_LOGIN_PROVIDERS } from '../config'
import { randomString, codeChallengeFor } from '../pkce'
import { clearAuthSession } from '../lib/authSession'

const PROVIDERS = [
  { id: 'google', label: 'Continue with Google', icon: 'G' },
  { id: 'facebook', label: 'Continue with Facebook', icon: 'f' },
  { id: 'github', label: 'Continue with GitHub', icon: 'GH' },
].filter((provider) => SOCIAL_LOGIN_PROVIDERS[provider.id])

async function startLogin(provider = '', forceLogin = false) {
  clearAuthSession(localStorage, sessionStorage)
  sessionStorage.setItem('shopno_auth_intent', 'login')
  sessionStorage.setItem('shopno_auth_method', provider || 'shopnoltd')
  const verifier = randomString(64)
  const challenge = await codeChallengeFor(verifier)
  const state = randomString(32)
  const nonce = randomString(32)

  sessionStorage.setItem('pkce_verifier', verifier)
  sessionStorage.setItem('oidc_state', state)
  sessionStorage.setItem('oidc_nonce', nonce)

  const paramsIn = new URLSearchParams(window.location.search)
  const incomingDomain = paramsIn.get('domain')
  const next = paramsIn.get('next')

  if (incomingDomain) {
    const value = incomingDomain
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9.-]/g, '')

    if (value) sessionStorage.setItem('pending_domain', value)
  }

  if (next && next.startsWith('/') && !next.startsWith('//')) {
    sessionStorage.setItem('post_login_next', next)
  }

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email',
    state,
    nonce,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  if (forceLogin) params.set('prompt', 'login')
  if (provider) params.set('kc_idp_hint', provider)

  window.location.assign(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`
  )
}

export default function Login() {
  const started = useRef(false)
  const [error, setError] = useState('')

  // No prompt=login: Keycloak can reuse an existing SSO session.
  // Use ?forceLogin=1 when the user explicitly needs to switch accounts.
  useEffect(() => {
    if (started.current) return
    started.current = true
    const forceLogin = new URLSearchParams(window.location.search).get('forceLogin') === '1'
    startLogin('', forceLogin).catch((err) => {
      setError(err?.message || 'Unable to start secure sign-in. Please try again.')
    })
  }, [])

  return (
    <main style={{ maxWidth: 520, width: '100%', margin: 'clamp(28px, 8vw, 60px) auto', padding: 'clamp(20px, 5vw, 32px)', fontFamily: 'system-ui, sans-serif', boxSizing: 'border-box' }}>
      <h1>Sign in to Shopnoltd</h1>
      <p style={{ color: '#64748b' }}>Checking your existing secure session…</p>
      {error && <p role='alert' style={{ color: '#b91c1c' }}>{error}</p>}
      <p style={{ textAlign: 'center' }}><a href='/login?forceLogin=1' style={{ color: '#0284c7' }}>Sign in with another account</a></p>
      <p style={{ color: '#64748b' }}>Use your Shopnoltd account{PROVIDERS.length ? ' or continue with an enabled social provider.' : '.'}</p>
      <button onClick={() => startLogin()} style={{ width: '100%', padding: 14, marginTop: 18, border: 0, borderRadius: 8, background: '#0ea5e9', color: 'white', fontSize: 16, cursor: 'pointer' }}>
        Continue with Shopnoltd
      </button>
      {PROVIDERS.length > 0 && <>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '24px 0', color: '#94a3b8' }}>
        <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} /> OR <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
      </div>
      <div style={{ display: 'grid', gap: 10 }}>
        {PROVIDERS.map((provider) => (
          <button key={provider.id} onClick={() => startLogin(provider.id, true)} style={{ width: '100%', padding: 13, border: '1px solid #cbd5e1', borderRadius: 8, background: 'white', color: '#0f172a', fontSize: 15, cursor: 'pointer' }}>
            <strong style={{ marginRight: 8 }}>{provider.icon}</strong>{provider.label}
          </button>
        ))}
      </div>
      </>}
      <p style={{ marginTop: 18, textAlign: 'center' }}><a href={KEYCLOAK_URL.replace(/\/$/, '') + '/realms/' + encodeURIComponent(KEYCLOAK_REALM) + '/login-actions/reset-credentials?client_id=' + encodeURIComponent(KEYCLOAK_CLIENT_ID)} style={{ color: '#0284c7', fontWeight: 600 }}>Forgot Password?</a></p>
      <p style={{ marginTop: 28, textAlign: 'center' }}>
        New to Shopnoltd? <a href="/register" style={{ color: '#0284c7' }}>Create an account</a>
      </p>
    </main>
  )
}
