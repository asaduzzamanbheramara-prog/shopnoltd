// Decode only the claims payload for OIDC transaction binding. Signature and access-token
// authorization remain the responsibility of Keycloak and the backend JWT verifiers.
export function hasExpectedOidcNonce(idToken, expectedNonce) {
  if (typeof idToken !== 'string' || !idToken || typeof expectedNonce !== 'string' || !expectedNonce) return false
  try {
    const parts = idToken.split('.')
    if (parts.length !== 3) return false
    const encoded = parts[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = encoded.padEnd(Math.ceil(encoded.length / 4) * 4, '=')
    const bytes = Uint8Array.from(atob(padded), character => character.charCodeAt(0))
    const claims = JSON.parse(new TextDecoder().decode(bytes))
    return claims.nonce === expectedNonce
  } catch {
    return false
  }
}
