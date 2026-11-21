import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'

const POLICY_CACHE = new Map()
import { adPlacementForPath } from './adPlacement.js'


async function readPolicy(hostname) {
  if (!POLICY_CACHE.has(hostname)) {
    const request = fetch('https://api.shopnoltd.dpdns.org/api/v1/ads/config?domain=' + encodeURIComponent(hostname), {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    }).then(async response => {
      if (!response.ok) throw new Error('Advertising policy unavailable')
      return response.json()
    }).catch(() => {
      // Fail closed for this render, but do not permanently cache a transient
      // network/429/5xx failure. A later mount can retry the public policy read.
      POLICY_CACHE.delete(hostname)
      return {
        hostname, enabled: false,
        networks: { adsense: false, adsterra: false, monetag: false, profiton: false },
        placements: { home: false, services: false, blog: false, feed: false, downloads: false },
      }
    })
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
