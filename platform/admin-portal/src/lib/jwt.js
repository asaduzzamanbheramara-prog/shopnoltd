export function decodeToken(token) {
  try { const payload = token.split('.')[1]; const base64 = payload.replace(/-/g, '+').replace(/_/g, '/'); const json = decodeURIComponent(atob(base64).split('').map(c => '%' + c.charCodeAt(0).toString(16).padStart(2, '0')).join('')); return JSON.parse(json) } catch { return null }
}
export function getRoles() {
  const token = localStorage.getItem('shopno_token'); if (!token) return []
  const payload = decodeToken(token); const roles = new Set(payload?.roles || [])
  for (const role of payload?.realm_access?.roles || []) roles.add(role)
  for (const role of payload?.resource_access?.['api-service']?.roles || []) roles.add(role)
  return [...roles]
}
export function isPlatformAdmin() { const roles = getRoles(); return roles.includes('platform_admin') || roles.includes('admin') }
