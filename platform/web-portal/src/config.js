// Keycloak connection info for the web-portal public client.
// Override at build time with Vite env vars (VITE_KEYCLOAK_URL etc.) --
// these defaults match docs/RUNBOOK.md / the cloudflared tunnel config.
export const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'https://auth.shopnoltd.dpdns.org'
export const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'shopnoltd'
export const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'web-portal'
export const REDIRECT_URI = `${window.location.origin}/callback`
