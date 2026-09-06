const TOKEN_URL = 'https://auth.shopnoltd.dpdns.org/realms/shopnoltd/protocol/openid-connect/token'
const CLIENT_ID = 'shopnoltd-web'

export async function tryRefresh() {
  const refreshToken = localStorage.getItem('shopno_refresh_token')
  if (!refreshToken) return null
  try {
    const res = await fetch(TOKEN_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        client_id: CLIENT_ID,
        refresh_token: refreshToken,
      }),
    })
    if (!res.ok) return null
    const data = await res.json()
    localStorage.setItem('shopno_token', data.access_token)
    localStorage.setItem('shopno_refresh_token', data.refresh_token)
    return data.access_token
  } catch {
    return null
  }
}

export function scheduleTokenRefresh() {
  const id = setInterval(tryRefresh, 4 * 60 * 1000) // every 4 min, access token expires every 5
  return () => clearInterval(id)
}
