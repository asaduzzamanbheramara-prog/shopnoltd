import { useEffect } from 'react'
import { ensureGoogleAnalyticsConfigured, getConsentPreferences } from '../lib/analytics'
import { useGoogleTagConsent } from '../lib/useAdvertisingConsent'

const MEASUREMENT_ID = 'G-JMMVDQQ08Z'

export default function GoogleTagLoader() {
  const allowed = useGoogleTagConsent()

  useEffect(() => {
    const selector = 'script[data-shopnoltd-gtag="true"]'
    const existing = document.querySelector(selector)

    if (!allowed) {
      existing?.remove()
      return
    }

    if (getConsentPreferences()?.analytics === true) ensureGoogleAnalyticsConfigured()

    if (existing) return
    const script = document.createElement('script')
    script.async = true
    script.src = 'https://www.googletagmanager.com/gtag/js?id=' + MEASUREMENT_ID
    script.dataset.shopnoltdGtag = 'true'
    document.head.appendChild(script)
  }, [allowed])

  return null
}
