// PKCE (Proof Key for Code Exchange) helpers -- lets a public SPA client do
// the OIDC Authorization Code flow safely without a client secret, per
// RFC 7636. Uses the browser's native Web Crypto API only, no dependency.

function base64url(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function randomString(len = 64) {
  const arr = new Uint8Array(len)
  crypto.getRandomValues(arr)
  return base64url(arr).slice(0, len)
}

export async function codeChallengeFor(verifier) {
  const data = new TextEncoder().encode(verifier)
  const digest = await crypto.subtle.digest('SHA-256', data)
  return base64url(digest)
}
