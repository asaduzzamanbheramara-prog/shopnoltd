import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL } from '../config'

const TOKEN_URL = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`

export async function tryRefresh() {
  const refreshToken = localStorage.getItem('shopno_refresh_token')
  if (!refreshToken) return null

  try {
    const res = await fetch(TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: KEYCLOAK_CLIENT_ID,
        refresh_token: refreshToken,
      }),
    })

    if (!res.ok) return null

    const data = await res.json()
    if (!data.access_token) return null

    localStorage.setItem('shopno_token', data.access_token)

    // Keycloak may rotate the refresh token, but it may also omit it.
    // Preserve the existing refresh token when no replacement is returned.
    if (data.refresh_token) {
      localStorage.setItem('shopno_refresh_token', data.refresh_token)
    }

    return data.access_token
  } catch {
    return null
  }
}

export function scheduleTokenRefresh() {
  const id = setInterval(tryRefresh, 4 * 60 * 1000) // every 4 min, access token expires every 5
  return () => clearInterval(id)
}
