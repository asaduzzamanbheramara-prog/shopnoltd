export function decodeToken(token) {
  try {
    const payload = token.split('.')[1]
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const json = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + c.charCodeAt(0).toString(16).padStart(2, '0'))
        .join('')
    )
    return JSON.parse(json)
  } catch {
    return null
  }
}

export function getRoles() {
  const token = localStorage.getItem('shopno_token')
  if (!token) return []
  const payload = decodeToken(token)
  const roles = new Set(payload?.roles || [])
  for (const role of payload?.realm_access?.roles || []) roles.add(role)
  for (const role of payload?.resource_access?.['api-service']?.roles || []) roles.add(role)
  return [...roles]
}

export function isPlatformAdmin() {
  const token = localStorage.getItem('shopno_token')
  const payload = token ? decodeToken(token) : null
  // Only realm roles (including the documented flat realm-role claim) grant
  // platform-wide access. Client-specific roles must never grant admin UI access.
  const realmRoles = new Set(payload?.roles || [])
  for (const role of payload?.realm_access?.roles || []) realmRoles.add(role)
  return realmRoles.has('platform_admin')
}
