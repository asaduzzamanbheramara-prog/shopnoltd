import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

const POLICY_CACHE = new Map()
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

async function readPolicy(hostname) {
  if (!POLICY_CACHE.has(hostname)) {
    const request = fetch('/api/v1/ads/config?domain=' + encodeURIComponent(hostname), {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    }).then(async response => {
      if (!response.ok) throw new Error('Advertising policy unavailable')
      return response.json()
    }).catch(() => ({
      hostname, enabled: false,
      networks: { adsense: false, adsterra: false, monetag: false, profiton: false },
      placements: { home: false, services: false, blog: false, feed: false, downloads: false },
    }))
    POLICY_CACHE.set(hostname, request)
  }
  return POLICY_CACHE.get(hostname)
}

export function invalidateAdPolicyCache(hostname) {
  if (hostname) POLICY_CACHE.delete(hostname)
  else POLICY_CACHE.clear()
}

export function useExternalAdPolicy(network) {
  const location = useLocation()
  const [policy, setPolicy] = useState(null)
  const hostname = window.location.hostname.toLowerCase()
  const placement = adPlacementForPath(location.pathname)

  useEffect(() => {
    let active = true
    readPolicy(hostname).then(value => { if (active) setPolicy(value) })
    return () => { active = false }
  }, [hostname])

  return Boolean(
    placement &&
    policy?.enabled === true &&
    policy?.networks?.[network] === true &&
    policy?.placements?.[placement] === true
  )
}
