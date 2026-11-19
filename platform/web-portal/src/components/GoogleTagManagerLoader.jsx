import { useEffect } from 'react'
import { useGoogleTagConsent } from '../lib/useAdvertisingConsent'

const CONTAINER_ID = 'GTM-PTHWL6TX'

/**
 * Load GTM only after the visitor grants an optional category.
 * Consent defaults are established in index.html before any Google script runs.
 * On revocation, the existing gtag consent update denies optional storage.
 */
export default function GoogleTagManagerLoader() {
  const allowed = useGoogleTagConsent()

  useEffect(() => {
    if (!allowed) return

    const selector = 'script[data-shopnoltd-gtm="true"]'
    if (document.querySelector(selector)) return

    window.dataLayer = window.dataLayer || []
    window.dataLayer.push({ 'gtm.start': Date.now(), event: 'gtm.js' })

    const script = document.createElement('script')
    script.async = true
    script.src = 'https://www.googletagmanager.com/gtm.js?id=' + CONTAINER_ID
    script.dataset.shopnoltdGtm = 'true'
    document.head.appendChild(script)
  }, [allowed])

  return null
}
