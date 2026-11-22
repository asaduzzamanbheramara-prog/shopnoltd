const EXCLUDED = [
  /^\/login(?:\/|$)/, /^\/register(?:\/|$)/, /^\/dashboard(?:\/|$)/,
  /^\/admin(?:\/|$)/, /^\/wallet(?:\/|$)/, /^\/transactions(?:\/|$)/,
  /^\/checkout(?:\/|$)/, /^\/payments?(?:\/|$)/, /^\/billing(?:\/|$)/,
  /^\/account(?:\/|$)/, /^\/auth(?:\/|$)/,
]

export function adPlacementForPath(pathname) {
  const path = pathname.replace(/\/+$/, '') || '/'
  if (EXCLUDED.some(pattern => pattern.test(path))) return null
  if (path === '/') return 'home'
  if (path === '/services' || path.startsWith('/services/')) return 'services'
  if (path === '/blog' || path.startsWith('/blog/')) return 'blog'
  if (path === '/feed' || path.startsWith('/feed/')) return 'feed'
  if (path === '/downloads' || path.startsWith('/downloads/')) return 'downloads'
  return null
}
