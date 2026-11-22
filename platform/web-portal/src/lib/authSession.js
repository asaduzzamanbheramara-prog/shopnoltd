export function isRefreshSessionCurrent(requestRefreshToken, currentRefreshToken) {
  return Boolean(requestRefreshToken && currentRefreshToken === requestRefreshToken)
}


// Clear credentials from the previous browser account before starting a new OIDC flow.
export function clearAuthTokens(storage) {
  for (const key of ['shopno_token', 'shopno_refresh_token', 'shopno_id_token']) {
    storage.removeItem(key)
  }
}

// Remove stale OIDC and account-specific session state without touching user preferences.
export function clearAuthSession(localStorage, sessionStorage) {
  clearAuthTokens(localStorage)
  for (const key of [
    'shopno_profile_provisioned',
    'pkce_verifier',
    'oidc_state',
    'pending_domain',
    'pending_referral_code',
    'pending_referral_category',
    'post_login_next',
  ]) sessionStorage.removeItem(key)
}
