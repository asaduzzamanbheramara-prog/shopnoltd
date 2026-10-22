import { useEffect, useRef } from 'react'

const ZONES = {
  '468x60': { key: '7747061d0c5ae776f68405dbeeab89fd', width: 468, height: 60, scriptUrl: 'https://bicea.org/22/7747061d0c5ae776f68405dbeeab89fd' },
  '160x300': { key: '01485acb7eefc95c30f7e25fb2986c58', width: 160, height: 300, scriptUrl: 'https://bicea.org/22/01485acb7eefc95c30f7e25fb2986c58' },
  '320x50': { key: '08bbf4b2a46b97a005c4d26ef1570b52', width: 320, height: 50, scriptUrl: 'https://bicea.org/22/08bbf4b2a46b97a005c4d26ef1570b52' },
  '728x90': { key: '8e53ca766e19e7f2777fbecab4ca6040', width: 728, height: 90, scriptUrl: 'https://bicea.org/22/8e53ca766e19e7f2777fbecab4ca6040' },
  '160x600': { key: '747cdd280fdc0b463f184d4662beaceb', width: 160, height: 600, scriptUrl: 'https://bicea.org/22/747cdd280fdc0b463f184d4662beaceb' },
  '300x250': { key: '253592d9ff11f220f7c319ff3ec1bde2', width: 300, height: 250, scriptUrl: 'https://bicea.org/22/253592d9ff11f220f7c319ff3ec1bde2' },
}

const NATIVE = {
  scriptUrl: 'https://bicea.org/21/38ffa3db02659ab0b305ed8c29df5ea3',
  containerId: 'container-38ffa3db02659ab0b305ed8c29df5ea3',
}

// Adsterra's standard banner snippets share window.atOptions. Serialize loading so
// a later zone cannot overwrite another zone's settings before its script executes.
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
    script.dataset.shopnoltdAdsterra = next.name
    script.setAttribute('data-cfasync', 'false')
    script.onload = () => {
      queue.running = false
      if (window.atOptions?.key === next.zone.key) delete window.atOptions
      runNext()
    }
    script.onerror = () => {
      queue.running = false
      if (window.atOptions?.key === next.zone.key) delete window.atOptions
      runNext()
    }
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
  padding: '10px',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: 8,
  overflow: 'hidden',
  border: '1px solid #e2e8f0',
  borderRadius: 12,
  background: '#fff',
}

function AdLabel() {
  return <span style={{ fontSize: 11, color: '#64748b', letterSpacing: '.06em', textTransform: 'uppercase' }}>Advertisement</span>
}

export function AdsterraBannerZone({ name, maxWidth = 760 }) {
  const zone = ZONES[name]
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container || !zone) return undefined
    const job = { name, zone, container }
    return enqueueZoneLoad(job)
  }, [name, zone])

  if (!zone) return null
  return <section aria-label={`Advertisement ${name}`} style={{ ...shellStyle, width: '100%', maxWidth }}>
    <AdLabel />
    <div ref={containerRef} style={{ width: zone.width, maxWidth: '100%', minHeight: zone.height, overflow: 'hidden', display: 'flex', justifyContent: 'center' }} />
  </section>
}

export function AdsterraNativeBanner() {
  const containerRef = useRef(null)
  useEffect(() => {
    const container = containerRef.current
    if (!container || container.querySelector('script[data-shopnoltd-native]')) return undefined
    const host = document.createElement('div')
    host.id = NATIVE.containerId
    host.style.minHeight = '100px'
    container.appendChild(host)
    const script = document.createElement('script')
    script.src = NATIVE.scriptUrl
    script.async = true
    script.setAttribute('data-cfasync', 'false')
    script.dataset.shopnoltdNative = 'true'
    container.appendChild(script)
    return () => {
      script.remove()
      host.remove()
    }
  }, [])
  return <section aria-label="Native advertisement" style={{ ...shellStyle, maxWidth: 760, alignItems: 'stretch' }}>
    <AdLabel />
    <div ref={containerRef} style={{ width: '100%', minHeight: 100 }} />
  </section>
}

export function AdsterraGlobalFormats() {
  useEffect(() => {
    const scripts = [
      { key: 'popunder', src: 'https://afders.org/1/09836d27bc58347743587df99b0dfe7f' },
      { key: 'socialbar', src: 'https://bicea.org/14/6709e7550b64cb74dbb906dc2ebb08e0' },
    ]
    const added = []
    for (const item of scripts) {
      if (document.querySelector(`script[data-shopnoltd-adsterra-global="${item.key}"]`)) continue
      const script = document.createElement('script')
      script.src = item.src
      script.async = true
      script.setAttribute('data-cfasync', 'false')
      script.dataset.shopnoltdAdsterraGlobal = item.key
      document.body.appendChild(script)
      added.push(script)
    }
    return () => {
      // Keep global-format scripts alive for the browser session. Removing the
      // element does not reliably undo listeners already registered by a provider.
    }
  }, [])
  return null
}

export function AdsterraSmartlink() {
  return <section aria-label="Sponsored link" style={{ ...shellStyle, maxWidth: 760, alignItems: 'flex-start', padding: 16 }}>
    <AdLabel />
    <p style={{ margin: 0, color: '#475569', lineHeight: 1.5 }}>Sponsored link. Opening it takes you to an external advertiser destination.</p>
    <a href="https://arwf.org/4/e15a69f3ca91af71dfca281a544d18e9" target="_blank" rel="sponsored noopener noreferrer" style={{ display: 'inline-block', padding: '9px 14px', borderRadius: 8, background: '#0369a1', color: '#fff', fontWeight: 700, textDecoration: 'none' }}>Visit sponsored link ↗</a>
  </section>
}
