import { KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, REDIRECT_URI } from '../config'
import { randomString, codeChallengeFor } from '../pkce'

// This used to POST directly to /api/v1/auth/login, an endpoint that never
// existed. Real login goes through Keycloak (every service in this platform
// authenticates via Keycloak OIDC) -- this also means Google/Facebook/GitHub
// social login buttons appear automatically on the Keycloak login screen,
// with no extra code needed here.

async function startLogin() {
  const verifier = randomString(64)
  const challenge = await codeChallengeFor(verifier)
  sessionStorage.setItem('pkce_verifier', verifier)

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    response_type: 'code',
    scope: 'openid profile email',
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })
  window.location.href = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params}`
}

export default function Login() {
  return (
    <div style={{ maxWidth: 360, margin: '64px auto', padding: 24, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' }}>
      <h2>Sign in to Shopnoltd</h2>
      <p style={{ color: '#64748b', margin: '12px 0 24px' }}>
        Continue with your email, or with Google / Facebook / GitHub.
      </p>
      <button onClick={startLogin} style={{ width: '100%', padding: 12, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8, fontSize: 16, cursor: 'pointer' }}>
        Continue to sign in
      </button>
    </div>
  )
}
