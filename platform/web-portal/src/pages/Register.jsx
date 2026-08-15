import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI } from '../config'
import { randomString, codeChallengeFor } from '../pkce'

const PROVIDERS = [
  { id: 'google', label: 'Sign up with Google', icon: 'G' },
  { id: 'facebook', label: 'Sign up with Facebook', icon: 'f' },
  { id: 'github', label: 'Sign up with GitHub', icon: 'GH' },
]

async function startSocialSignup(provider) {
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
    kc_idp_hint: provider,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  window.location.assign(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`
  )
}

async function startLocalSignup() {
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
  return (
    <main
      style={{
        maxWidth: 520,
        margin: '60px auto',
        padding: 32,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Create your Shopnoltd account</h1>

      <p style={{ color: '#64748b' }}>
        Create an account with Shopnoltd or use one of the social providers.
      </p>

      <button
        onClick={startLocalSignup}
        style={{
          width: '100%',
          padding: 14,
          marginTop: 18,
          border: 0,
          borderRadius: 8,
          background: '#0ea5e9',
          color: 'white',
          fontSize: 16,
          cursor: 'pointer',
        }}
      >
        Register with Shopnoltd
      </button>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          margin: '24px 0',
          color: '#94a3b8',
        }}
      >
        <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
        OR
        <div style={{ flex: 1, height: 1, background: '#e2e8f0' }} />
      </div>

      <div style={{ display: 'grid', gap: 10 }}>
        {PROVIDERS.map((provider) => (
          <button
            key={provider.id}
            onClick={() => startSocialSignup(provider.id)}
            style={{
              width: '100%',
              padding: 13,
              border: '1px solid #cbd5e1',
              borderRadius: 8,
              background: 'white',
              color: '#0f172a',
              fontSize: 15,
              cursor: 'pointer',
            }}
          >
            <strong style={{ marginRight: 8 }}>{provider.icon}</strong>
            {provider.label}
          </button>
        ))}
      </div>

      <p style={{ marginTop: 28, textAlign: 'center' }}>
        Already have an account?{' '}
        <a href="/login" style={{ color: '#0284c7' }}>
          Sign in
        </a>
      </p>
    </main>
  )
}
