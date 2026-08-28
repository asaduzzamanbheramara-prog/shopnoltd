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
  return payload?.roles || []
}

export function isPlatformAdmin() {
  const roles = getRoles()
  return roles.includes('platform_admin') || roles.includes('admin')
}
