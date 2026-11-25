// Affiliate task redirects must remain on the configured Shopnoltd API host.
export function resolveAffiliateTaskUrl(taskUrl, apiBaseUrl) {
  let apiBase
  let destination
  try {
    apiBase = new URL(apiBaseUrl)
    destination = new URL(taskUrl, apiBase)
  } catch {
    throw new Error('The task destination could not be verified.')
  }

  if (
    apiBase.protocol !== 'https:' ||
    destination.protocol !== 'https:' ||
    destination.origin !== apiBase.origin ||
    !destination.pathname.startsWith('/api/v1/affiliate/go/') ||
    destination.username ||
    destination.password
  ) {
    throw new Error('The task link is not a verified Shopnoltd destination.')
  }

  return destination.href
}
