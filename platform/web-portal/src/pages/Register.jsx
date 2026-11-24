import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI, SOCIAL_LOGIN_PROVIDERS } from '../config'
import { randomString, codeChallengeFor } from '../pkce'
import { clearAuthSession } from '../lib/authSession'
import { Github, UserRoundPlus } from 'lucide-react'

const PROVIDERS = [
  { id: 'google', feature: 'google', label: 'Sign up with Google', icon: 'G' },
  { id: 'facebook', feature: 'facebook', label: 'Sign up with Facebook', icon: 'f' },
  { id: 'github', feature: 'github', label: 'Sign up with GitHub', icon: 'GH' },
].filter((provider) => SOCIAL_LOGIN_PROVIDERS[provider.feature])

async function startSocialSignup(provider) {
  clearAuthSession(localStorage, sessionStorage)
  sessionStorage.setItem('shopno_auth_intent', 'sign_up')
  sessionStorage.setItem('shopno_auth_method', provider)
  const verifier = randomString(64)
  const challenge = await codeChallengeFor(verifier)
  const state = randomString(32)

  sessionStorage.setItem('pkce_verifier', verifier)
  sessionStorage.setItem('oidc_state', state)

  const searchParams = new URLSearchParams(window.location.search)
  const incomingDomain = searchParams.get('domain')
  const incomingReferral = searchParams.get('ref')
  const incomingProfileCategory = searchParams.get('category')

  if (incomingReferral) {
    const value = incomingReferral.trim().toUpperCase()
    if (value) sessionStorage.setItem('pending_referral_code', value)
  }
  if (incomingProfileCategory?.trim()) sessionStorage.setItem('pending_referral_category', incomingProfileCategory.trim().toLowerCase())

  if (incomingDomain) {
    const value = incomingDomain
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]/g, '')

    if (value) {
      sessionStorage.setItem('pending_domain', value)
    }
  }

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email',
    state,
    kc_idp_hint: provider + '-signup',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  window.location.assign(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`
  )
}

async function startLocalSignup() {
  clearAuthSession(localStorage, sessionStorage)
  sessionStorage.setItem('shopno_auth_intent', 'sign_up')
  sessionStorage.setItem('shopno_auth_method', 'shopnoltd')
  const searchParams = new URLSearchParams(window.location.search)
  const incomingReferral = searchParams.get('ref')
  const incomingProfileCategory = searchParams.get('category')
  if (incomingReferral?.trim()) sessionStorage.setItem('pending_referral_code', incomingReferral.trim().toUpperCase())
  if (incomingProfileCategory?.trim()) sessionStorage.setItem('pending_referral_category', incomingProfileCategory.trim().toLowerCase())
  const verifier = randomString(64)
  const challenge = await codeChallengeFor(verifier)
  const state = randomString(32)

  sessionStorage.setItem('pkce_verifier', verifier)
  sessionStorage.setItem('oidc_state', state)

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email',
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  window.location.assign(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/registrations?${params.toString()}`
  )
}

export default function Register() {
  const shell = { width: 'min(calc(100vw - 56px), 480px)' , maxWidth: 480, minWidth: 0, margin: 'clamp(24px, 7vw, 64px) auto', padding: 'clamp(16px, 4vw, 24px)', boxSizing: 'border-box', fontFamily: 'system-ui, sans-serif', color: '#0f172a' }
  const card = { width: '100%', minWidth: 0, boxSizing: 'border-box', padding: 'clamp(20px, 5vw, 34px)', border: '1px solid #e2e8f0', borderRadius: 18, background: '#fff', boxShadow: '0 12px 36px rgba(15, 23, 42, 0.07)' }
  const primary = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, width: '100%', minWidth: 0, boxSizing: 'border-box', minHeight: 50, padding: '12px 16px', border: 0, borderRadius: 10, background: '#0284c7', color: '#fff', fontSize: 15, fontWeight: 650, cursor: 'pointer' }
  const social = { display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, width: '100%', minWidth: 0, boxSizing: 'border-box', minHeight: 48, padding: '11px 12px', border: '1px solid #cbd5e1', borderRadius: 10, background: '#fff', color: '#0f172a', fontSize: 14, fontWeight: 600, cursor: 'pointer' }
  return (
    <main style={shell}>
      <section style={card} aria-labelledby="register-title">
        <div style={{ display: 'grid', placeItems: 'center', width: 48, height: 48, marginBottom: 20, borderRadius: 14, background: '#e0f2fe', color: '#0369a1' }}><UserRoundPlus size={25} aria-hidden="true" /></div>
        <h1 id="register-title" style={{ margin: 0, fontSize: 'clamp(25px, 5vw, 30px)', lineHeight: 1.2, letterSpacing: '-0.04em', overflowWrap: 'anywhere' }}>Create your Shopnoltd account</h1>
        <p style={{ margin: '12px 0 24px', color: '#64748b', fontSize: 14, lineHeight: 1.65 }}>{'Create an account with Shopnoltd' + (PROVIDERS.length ? ' or use an enabled social provider.' : '.')}</p>
        <button type="button" onClick={startLocalSignup} style={primary}><UserRoundPlus size={18} aria-hidden="true" /> Register with Shopnoltd</button>
        {PROVIDERS.length > 0 && <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, margin: '23px 0', color: '#94a3b8', fontSize: 11, fontWeight: 700, letterSpacing: '0.12em' }}><span style={{ flex: 1, height: 1, background: '#e2e8f0' }} /> OR CONTINUE WITH <span style={{ flex: 1, height: 1, background: '#e2e8f0' }} /></div>
          <div style={{ display: 'grid', gap: 10 }}>
            {PROVIDERS.map((provider) => <button key={provider.id} type="button" onClick={() => startSocialSignup(provider.id)} style={social}>
              {provider.feature === 'google' ? <svg width="19" height="19" viewBox="0 0 48 48" aria-hidden="true"><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.25 5.48-4.73 7.18l7.63 5.92c4.45-4.1 7.14-10.14 7.14-17.57Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.9-5.78l-7.63-5.92c-2.12 1.42-4.84 2.27-8.27 2.27-6.26 0-11.57-4.22-13.46-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"/><path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.19A23.9 23.9 0 0 0 0 24c0 3.88.93 7.55 2.56 10.78l7.97-6.19Z"/><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/></svg> : provider.feature === 'github' ? <Github size={19} aria-hidden="true" /> : <svg width="19" height="19" viewBox="0 0 24 24" aria-hidden="true"><path fill="#1877F2" d="M24 12a12 12 0 1 0-13.875 11.85v-8.38H7.08V12h3.045V9.356c0-3.005 1.79-4.666 4.53-4.666 1.312 0 2.684.234 2.684.234v2.95h-1.512c-1.49 0-1.953.925-1.953 1.874V12h3.323l-.531 3.47h-2.792v8.38A12.002 12.002 0 0 0 24 12Z"/></svg>}
              {provider.label}
            </button>)}
          </div>
        </>}
        <p style={{ margin: '25px 0 0', paddingTop: 20, borderTop: '1px solid #f1f5f9', textAlign: 'center', color: '#64748b', fontSize: 13 }}>Already have an account? <a href="/login" style={{ color: '#0369a1', fontWeight: 650, textDecoration: 'none' }}>Sign in</a></p>
      </section>
      <p style={{ margin: '14px auto 0', maxWidth: 420, textAlign: 'center', color: '#94a3b8', fontSize: 11, lineHeight: 1.6 }}>By creating an account, you agree to Shopnoltd's <a href="/terms" style={{ color: '#64748b', textDecoration: 'underline' }}>Terms</a> and <a href="/privacy" style={{ color: '#64748b', textDecoration: 'underline' }}>Privacy Policy</a>.</p>
    </main>
  )
}
