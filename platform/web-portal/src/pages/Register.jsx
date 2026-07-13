import { KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, REDIRECT_URI } from '../config'
import { randomString, codeChallengeFor } from '../pkce'

// Keycloak has a built-in registration form (Realm Settings -> Login ->
// "User registration" must be enabled). This hits the same PKCE flow as
// Login.jsx but starts on Keycloak's /registrations endpoint instead of
// /auth, landing back on the same /callback page either way.

async function startRegister() {
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
  window.location.href = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/registrations?${params}`
}

export default function Register() {
  return (
    <div style={{ maxWidth: 360, margin: '64px auto', padding: 24, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)', textAlign: 'center' }}>
      <h2>Create your Shopnoltd account</h2>
      <p style={{ color: '#64748b', margin: '12px 0 24px' }}>
        Sign up with email, or with Google / Facebook / GitHub.
      </p>
      <button onClick={startRegister} style={{ width: '100%', padding: 12, background: '#10b981', color: 'white', border: 0, borderRadius: 8, fontSize: 16, cursor: 'pointer' }}>
        Create account
      </button>
      <p style={{ marginTop: 16, fontSize: 14 }}>
        Already have an account? <a href="/login">Sign in</a>
      </p>
    </div>
  )
}
