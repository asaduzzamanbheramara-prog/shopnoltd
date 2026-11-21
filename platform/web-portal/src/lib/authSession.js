export function isRefreshSessionCurrent(requestRefreshToken, currentRefreshToken) {
  return Boolean(requestRefreshToken && currentRefreshToken === requestRefreshToken)
}

export function clearAuthTokens(storage) {
  if (!storage) return
  for (const key of ['shopno_token', 'shopno_refresh_token', 'shopno_id_token']) {
    storage.removeItem(key)
  }
}
