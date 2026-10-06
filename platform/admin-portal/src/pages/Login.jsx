import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI } from '../config'
import { randomString, codeChallengeFor } from '../pkce'
async function startLogin() {
  const verifier = randomString(64); const challenge = await codeChallengeFor(verifier); const state = randomString(32)
  sessionStorage.setItem('pkce_verifier', verifier); sessionStorage.setItem('oidc_state', state)
  const next = new URLSearchParams(window.location.search).get('next'); if (next && next.startsWith('/') && !next.startsWith('//')) sessionStorage.setItem('post_login_next', next)
  const params = new URLSearchParams({ client_id: KEYCLOAK_CLIENT_ID, redirect_uri: REDIRECT_URI, response_type: 'code', scope: 'openid profile email', state, code_challenge: challenge, code_challenge_method: 'S256' })
  window.location.assign(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`)
}
export default function Login() { return <main style={{ maxWidth: 520, margin: '80px auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}><h1>Sign in to Shopnoltd</h1><p style={{ color: '#64748b' }}>Administrator access requires an authorized Shopnoltd account.</p><button onClick={startLogin} style={{ width: '100%', padding: 14, border: 0, borderRadius: 8, background: '#0ea5e9', color: 'white', fontSize: 16, cursor: 'pointer' }}>Continue with Shopnoltd</button><p style={{ marginTop: 24, color: '#64748b', fontSize: 13 }}>Shopnoltd Admin Portal</p></main> }
