export function isRefreshSessionCurrent(requestRefreshToken, currentRefreshToken) {
  return Boolean(requestRefreshToken && currentRefreshToken === requestRefreshToken)
}
