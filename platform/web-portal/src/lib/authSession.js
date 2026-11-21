export function isRefreshSessionCurrent(requestRefreshToken, currentRefreshToken) {
  return Boolean(requestRefreshToken && currentRefreshToken === requestRefreshToken)
}

export function clearAuthTokens(storage) {
  if (!storage) return
  for (const key of ['shopno_token', 'shopno_refresh_token', 'shopno_id_token', 'shopno_user_id']) {
    storage.removeItem(key)
  }
}

export function clearPendingAuthState(storage) {
  if (!storage) return
  for (const key of [
    'shopno_profile_provisioned',
    'pkce_verifier',
    'oidc_state',
    'pending_domain',
    'pending_referral_code',
    'pending_referral_category',
    'post_login_next',
    'shopno_auth_intent',
    'shopno_auth_method',
  ]) storage.removeItem(key)
}
