import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI } from '../config'
export default function Callback() {
  const [error, setError] = useState(null); const navigate = useNavigate()
  useEffect(() => {
    const params = new URLSearchParams(window.location.search); const code = params.get('code'); const returnedState = params.get('state'); const oauthError = params.get('error'); const verifier = sessionStorage.getItem('pkce_verifier'); const expectedState = sessionStorage.getItem('oidc_state')
    if (oauthError) { setError(params.get('error_description') || oauthError); return }
    if (!code || !verifier || returnedState !== expectedState) { setError('Authentication state validation failed. Please try again.'); return }
    const body = new URLSearchParams({ grant_type: 'authorization_code', client_id: KEYCLOAK_CLIENT_ID, code, redirect_uri: REDIRECT_URI, code_verifier: verifier })
    fetch(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body }).then(async response => { const data = await response.json(); if (!response.ok || !data.access_token) throw new Error(data.error_description || data.error || 'Authentication failed.'); return data }).then(data => { localStorage.setItem('shopno_token', data.access_token); if (data.refresh_token) localStorage.setItem('shopno_refresh_token', data.refresh_token); sessionStorage.removeItem('pkce_verifier'); sessionStorage.removeItem('oidc_state'); const next = sessionStorage.getItem('post_login_next'); sessionStorage.removeItem('post_login_next'); navigate(next && next.startsWith('/') && !next.startsWith('//') ? next : '/', { replace: true }) }).catch(err => setError(err.message))
  }, [navigate])
  if (error) return <main style={{ maxWidth: 640, margin: '80px auto', padding: 24 }}><h2>Authentication failed</h2><p>{error}</p><a href="/login">Return to login</a></main>
  return <main style={{ maxWidth: 640, margin: '80px auto', padding: 24, textAlign: 'center' }}>Completing Shopnoltd sign in…</main>
}
