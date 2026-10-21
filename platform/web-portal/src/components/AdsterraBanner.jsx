import { useEffect, useRef } from 'react'

const ADSTERRA_ZONE = {
  key: '253592d9ff11f220f7c319ff3ec1bde2',
  width: 300,
  height: 250,
  scriptUrl: 'https://bicea.org/22/253592d9ff11f220f7c319ff3ec1bde2',
}

/**
 * Loads one Adsterra 300x250 display zone after the component mounts.
 * Keep only one instance of this zone on a page because Adsterra's
 * synchronous snippet uses the global window.atOptions object.
 */
export default function AdsterraBanner() {
  const containerRef = useRef(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return undefined

    // Avoid adding duplicate scripts if the component remounts.
    const existing = container.querySelector('script[data-shopnoltd-adsterra="300x250"]')
    if (existing) return undefined

    window.atOptions = {
      key: ADSTERRA_ZONE.key,
      format: 'iframe',
      height: ADSTERRA_ZONE.height,
      width: ADSTERRA_ZONE.width,
      params: {},
    }

    const script = document.createElement('script')
    script.src = ADSTERRA_ZONE.scriptUrl
    script.async = false
    script.dataset.shopnoltdAdsterra = '300x250'
    script.referrerPolicy = 'strict-origin-when-cross-origin'
    container.appendChild(script)

    return () => {
      script.remove()
      if (containerRef.current) containerRef.current.replaceChildren()
      if (window.atOptions?.key === ADSTERRA_ZONE.key) {
        delete window.atOptions
      }
    }
  }, [])

  return (
    <section
      aria-label="Advertisement"
      style={{
        width: '100%',
        maxWidth: 340,
        minHeight: 280,
        margin: '28px auto',
        padding: '12px 8px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'flex-start',
        gap: 8,
        boxSizing: 'border-box',
        overflow: 'hidden',
        border: '1px solid #e2e8f0',
        borderRadius: 12,
        background: '#fff',
      }}
    >
      <span style={{ fontSize: 11, color: '#64748b', letterSpacing: '.06em', textTransform: 'uppercase' }}>
        Advertisement
      </span>
      <div
        ref={containerRef}
        style={{
          width: ADSTERRA_ZONE.width,
          maxWidth: '100%',
          minHeight: ADSTERRA_ZONE.height,
          overflow: 'hidden',
          display: 'flex',
          justifyContent: 'center',
        }}
      />
    </section>
  )
}
