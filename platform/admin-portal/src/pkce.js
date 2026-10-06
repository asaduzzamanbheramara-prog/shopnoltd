function base64url(buf) {
  return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}
export function randomString(len = 64) {
  const arr = new Uint8Array(len); crypto.getRandomValues(arr); return base64url(arr).slice(0, len)
}
export async function codeChallengeFor(verifier) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier)); return base64url(digest)
}
