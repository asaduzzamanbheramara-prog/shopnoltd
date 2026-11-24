import { useEffect, useRef } from 'react'
import { useAdvertisingConsent } from '../lib/useAdvertisingConsent'

// Only the publisher-approved 300x250 display banner is enabled.
// Other Adsterra formats (native, social bar, smartlink, popunder, and alternate
// banner sizes) are intentionally not configured or loaded by this application.
const ZONE_300X250 = {
  key: '253592d9ff11f220f7c319ff3ec1bde2',
  width: 300,
  height: 250,
  scriptUrl: 'https://bicea.org/22/253592d9ff11f220f7c319ff3ec1bde2',
}

// Serialize the publisher script so window.atOptions cannot be overwritten
// before the corresponding zone script reads it.
function enqueueZoneLoad(job) {
  if (!window.__shopnoltdAdsterraQueue) {
    window.__shopnoltdAdsterraQueue = { jobs: [], running: false }
  }
  const queue = window.__shopnoltdAdsterraQueue
  queue.jobs.push(job)

  const runNext = () => {
    if (queue.running || !queue.jobs.length) return
    queue.running = true
    const next = queue.jobs.shift()
    window.atOptions = {
      key: next.zone.key,
      format: 'iframe',
      height: next.zone.height,
      width: next.zone.width,
      params: {},
    }
    const script = document.createElement('script')
    script.src = next.zone.scriptUrl
    script.async = false
    script.dataset.shopnoltdAdsterra = '300x250'
    script.setAttribute('data-cfasync', 'false')
    const finish = () => {
      queue.running = false
      if (window.atOptions?.key === next.zone.key) delete window.atOptions
      runNext()
    }
    script.onload = finish
    script.onerror = finish
    next.container.appendChild(script)
  }

  runNext()
  return () => {
    const index = queue.jobs.indexOf(job)
    if (index >= 0) queue.jobs.splice(index, 1)
  }
}

const shellStyle = {
  boxSizing: 'border-box',
  margin: '24px auto',
  padding: 4,
  width: '100%',
  maxWidth: '100%',
  minWidth: 0,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 8,
  overflow: 'hidden',
  border: '1px solid #e2e8f0',
  borderRadius: 12,
  background: '#fff',
}

export function AdsterraBannerZone({ maxWidth = 340 }) {
  const allowed = useAdvertisingConsent()
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!allowed || !container) return undefined
    const job = { zone: ZONE_300X250, container }
    return enqueueZoneLoad(job)
  }, [allowed])

  if (!allowed) return null
  return (
    <section aria-label="Advertisement 300x250" style={{ ...shellStyle, maxWidth }}>
      <span style={{ fontSize: 11, color: '#64748b', letterSpacing: '.06em', textTransform: 'uppercase' }}>Advertisement</span>
      <div ref={containerRef} style={{ width: 300, maxWidth: '100%', minHeight: 250, overflow: 'hidden', display: 'flex', justifyContent: 'center' }} />
    </section>
  )
}
// Deprecated non-homepage ad placements intentionally disabled.
// Homepage uses the single 300x250 zone from AdsterraBanner.jsx only.
export function AdsterraResponsiveBanner() { return null }
