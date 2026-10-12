const TOKEN_URL = 'https://auth.shopnoltd.dpdns.org/realms/shopnoltd/protocol/openid-connect/token'
const CLIENT_ID = 'shopnoltd-web'
let refreshPromise = null

export async function tryRefresh() {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    try {
      const refreshToken = localStorage.getItem('shopno_refresh_token')
      if (!refreshToken) return null

      const res = await fetch(TOKEN_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({
          grant_type: 'refresh_token',
          client_id: CLIENT_ID,
          refresh_token: refreshToken,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        if ((res.status === 400 || res.status === 401) &&
            ['invalid_grant', 'invalid_token'].includes(data.error)) {
          localStorage.removeItem('shopno_token')
          localStorage.removeItem('shopno_refresh_token')
        }
        return null
      }
      if (!data.access_token) return null
      localStorage.setItem('shopno_token', data.access_token)
      // Some providers omit a replacement refresh token; preserve the current one.
      if (data.refresh_token) localStorage.setItem('shopno_refresh_token', data.refresh_token)
      return data.access_token
    } catch {
      return null
    } finally {
      refreshPromise = null
    }
  })()

  return refreshPromise
}
