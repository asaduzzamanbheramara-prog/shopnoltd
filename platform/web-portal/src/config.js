// Keycloak connection info for the web-portal public client.
// Override at build time with Vite env vars (VITE_KEYCLOAK_URL etc.).
// The empty fallback also keeps config importable by Node-based unit tests.
const env = import.meta.env || {}
const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:5173'

export const KEYCLOAK_URL = env.VITE_KEYCLOAK_URL || 'https://auth.shopnoltd.dpdns.org'
export const KEYCLOAK_REALM = env.VITE_KEYCLOAK_REALM || 'shopnoltd'
export const KEYCLOAK_CLIENT_ID = env.VITE_KEYCLOAK_CLIENT_ID || 'shopnoltd-web'
export const REDIRECT_URI = `${origin}/callback`

export const API_URL = env.VITE_API_URL || ''

// Social sign-in buttons stay hidden until matching OAuth credentials are provisioned in Keycloak.
export const SOCIAL_LOGIN_PROVIDERS = {
  google: env.VITE_SOCIAL_LOGIN_GOOGLE === 'true',
  facebook: env.VITE_SOCIAL_LOGIN_FACEBOOK === 'true',
  github: env.VITE_SOCIAL_LOGIN_GITHUB === 'true',
}
