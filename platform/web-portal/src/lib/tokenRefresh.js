import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL } from '../config'
import { isRefreshSessionCurrent } from './authSession'

const TOKEN_URL = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`

// Keycloak refresh-token rotation means concurrent refresh requests can invalidate
// each other. Keep one refresh request in flight and let all callers share it.
let refreshPromise = null
let refreshPromiseToken = null

export async function tryRefresh() {
  const refreshToken = localStorage.getItem('shopno_refresh_token')
  if (!refreshToken) return null
  if (refreshPromise && refreshPromiseToken === refreshToken) return refreshPromise

  const requestRefreshToken = refreshToken
  refreshPromiseToken = requestRefreshToken
  const requestPromise = (async () => {
    try {

      // A refresh can finish after logout or after another user signs in on the
      // same browser. Never let an older session overwrite the newer session.
      const isStillCurrentSession = () =>
        isRefreshSessionCurrent(refreshToken, localStorage.getItem('shopno_refresh_token'))

      const res = await fetch(TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          client_id: KEYCLOAK_CLIENT_ID,
          refresh_token: refreshToken,
        }),
      })

      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        // A revoked/expired refresh token is terminal; clear stale local auth.
        // Preserve tokens on transient server/network errors so users can retry.
        if ((res.status === 400 || res.status === 401) &&
            ['invalid_grant', 'invalid_token'].includes(data.error) &&
            isStillCurrentSession()) {
          localStorage.removeItem('shopno_token')
          localStorage.removeItem('shopno_refresh_token')
          localStorage.removeItem('shopno_id_token')
        }
        return null
      }
      if (!data.access_token || !isStillCurrentSession()) return null

      localStorage.setItem('shopno_token', data.access_token)

      // Keycloak may rotate the refresh token, but it may also omit it.
      // Preserve the existing refresh token when no replacement is returned.
      if (data.refresh_token) {
        localStorage.setItem('shopno_refresh_token', data.refresh_token)
      }
      if (data.id_token) {
        localStorage.setItem('shopno_id_token', data.id_token)
      }

      return data.access_token
    } catch {
      return null
    } finally {
      // Do not clear a newer user's in-flight refresh promise.
      if (refreshPromiseToken === requestRefreshToken) {
        refreshPromise = null
        refreshPromiseToken = null
      }
    }
  })()

  refreshPromise = requestPromise
  return requestPromise
}

export function scheduleTokenRefresh() {
  const id = setInterval(tryRefresh, 2 * 60 * 1000) // refresh well before the short-lived access token expires
  return () => clearInterval(id)
}
