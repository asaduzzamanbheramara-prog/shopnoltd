// Keycloak connection info for the web-portal public client.
// Override at build time with Vite env vars (VITE_KEYCLOAK_URL etc.) --
// these defaults match docs/RUNBOOK.md / the cloudflared tunnel config.
export const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'https://auth.shopnoltd.dpdns.org'
export const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'shopnoltd'
export const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'shopnoltd-web'
export const REDIRECT_URI = `${window.location.origin}/callback`

export const API_URL = import.meta.env.VITE_API_URL || ''

// Social sign-in buttons stay hidden until matching OAuth credentials are provisioned in Keycloak.
export const SOCIAL_LOGIN_PROVIDERS = {
  google: import.meta.env.VITE_SOCIAL_LOGIN_GOOGLE === 'true',
  facebook: import.meta.env.VITE_SOCIAL_LOGIN_FACEBOOK === 'true',
  github: import.meta.env.VITE_SOCIAL_LOGIN_GITHUB === 'true',
}
