import { useEffect, useRef } from 'react'
import { useAdvertisingConsent } from '../lib/useAdvertisingConsent'
import { useExternalAdPolicy } from '../lib/useExternalAdPolicy'

// Single publisher-approved 300x250 display banner. Other Adsterra formats are disabled.
const ZONE = {
  key: '253592d9ff11f220f7c319ff3ec1bde2',
  width: 300,
  height: 250,
  scriptUrl: 'https://bicea.org/22/253592d9ff11f220f7c319ff3ec1bde2',
}

function enqueueZoneLoad(job) {
  if (!window.__shopnoltdAdsterraQueue) window.__shopnoltdAdsterraQueue = { jobs: [], running: false, current: null }
  const queue = window.__shopnoltdAdsterraQueue
  job.cancelled = false
  queue.jobs.push(job)

  const finish = (current) => {
    if (queue.current !== current) return
    queue.running = false
    queue.current = null
    if (window.atOptions?.key === current.zone.key) delete window.atOptions
    runNext()
  }
  const runNext = () => {
    if (queue.running) return
    const next = queue.jobs.shift()
    if (!next) return
    if (next.cancelled || !next.container.isConnected) return runNext()
    queue.running = true
    queue.current = next
    window.atOptions = { key: next.zone.key, format: 'iframe', height: next.zone.height, width: next.zone.width, params: {} }
    const script = document.createElement('script')
    next.script = script
    script.src = next.zone.scriptUrl
    script.async = false
    script.dataset.shopnoltdAdsterra = '300x250'
    script.setAttribute('data-cfasync', 'false')
    script.onload = () => finish(next)
    script.onerror = () => finish(next)
    next.container.appendChild(script)
  }
  runNext()
  return () => {
    job.cancelled = true
    const index = queue.jobs.indexOf(job)
    if (index >= 0) queue.jobs.splice(index, 1)
    if (queue.current === job) {
      job.script?.remove()
      queue.running = false
      queue.current = null
      if (window.atOptions?.key === job.zone.key) delete window.atOptions
      runNext()
    }
  }
}

const shellStyle = {
  boxSizing: 'border-box', margin: '24px auto', padding: 4, width: '100%', maxWidth: '100%', minWidth: 0,
  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8, overflow: 'hidden',
  border: '1px solid #e2e8f0', borderRadius: 12, background: '#fff',
}

export function AdsterraBannerZone({ maxWidth = 340 }) {
  const consentAllowed = useAdvertisingConsent()
  const policyAllowed = useExternalAdPolicy('adsterra')
  const allowed = consentAllowed && policyAllowed
  const containerRef = useRef(null)
  useEffect(() => {
    const container = containerRef.current
    if (!allowed || !container) return undefined
    return enqueueZoneLoad({ zone: ZONE, container })
  }, [allowed])
  if (!allowed) return null
  return <section aria-label="Advertisement 300x250" style={{ ...shellStyle, maxWidth }}>
    <span style={{ fontSize: 11, color: '#64748b', letterSpacing: '.06em', textTransform: 'uppercase' }}>Advertisement</span>
    <div ref={containerRef} style={{ width: 300, maxWidth: '100%', minHeight: 250, overflow: 'hidden', display: 'flex', justifyContent: 'center' }} />
  </section>
}

// Kept as a compatibility export for routes/components that referenced it. No ad loads.
export function AdsterraResponsiveBanner() { return null }
