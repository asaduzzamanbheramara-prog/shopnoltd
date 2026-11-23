export function isRefreshSessionCurrent(requestRefreshToken, currentRefreshToken) {
  return Boolean(requestRefreshToken && currentRefreshToken === requestRefreshToken)
}

// Remove every token belonging to the previous browser account before a new
// OIDC authorization flow begins or a new authorization-code response is saved.
export function clearAuthTokens(storage) {
  for (const key of ['shopno_token', 'shopno_refresh_token', 'shopno_id_token']) {
    storage.removeItem(key)
  }
}

// Start a clean OIDC flow when a browser changes accounts or begins registration.
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
