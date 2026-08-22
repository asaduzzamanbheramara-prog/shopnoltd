import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI } from '../config'
import { randomString, codeChallengeFor } from '../pkce'

const PROVIDERS = [
  { id: 'google', label: 'Continue with Google', icon: 'G' },
  { id: 'facebook', label: 'Continue with Facebook', icon: 'f' },
  { id: 'github', label: 'Continue with GitHub', icon: 'GH' },
]

async function startLogin(provider = '') {
  const verifier = randomString(64)
  const challenge = await codeChallengeFor(verifier)
  const state = randomString(32)

  sessionStorage.setItem('pkce_verifier', verifier)
  sessionStorage.setItem('oidc_state', state)

  const incomingDomain =
    new URLSearchParams(window.location.search).get('domain')

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
    code_challenge: challenge,
    code_challenge_method: 'S256',
  })

  if (provider) {
    params.set('kc_idp_hint', provider)
  }

  window.location.assign(
    `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth?${params.toString()}`
  )
}

export default function Login() {
  return (
    <main
      style={{
        maxWidth: 520,
        margin: '60px auto',
        padding: 32,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Sign in to Shopnoltd</h1>

      <p style={{ color: '#64748b' }}>
        Use your Shopnoltd account or continue with a social provider.
      </p>

      <button
        onClick={() => startLogin()}
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
        Continue with Shopnoltd
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
            onClick={() => startLogin(provider.id)}
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
        New to Shopnoltd?{' '}
        <a href="/register" style={{ color: '#0284c7' }}>
          Create an account
        </a>
      </p>
    </main>
  )
}
