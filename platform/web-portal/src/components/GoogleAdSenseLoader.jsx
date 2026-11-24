import { useEffect } from 'react'
import { useAdvertisingConsent } from '../lib/useAdvertisingConsent'
import { useExternalAdPolicy } from '../lib/useExternalAdPolicy'

const ADSENSE_CLIENT = 'ca-pub-4532970890139771'

export default function GoogleAdSenseLoader() {
  const consentAllowed = useAdvertisingConsent()
  const policyAllowed = useExternalAdPolicy('adsense')
  const allowed = consentAllowed && policyAllowed

  useEffect(() => {
    const selector = 'script[data-shopnoltd-adsense="true"]'
    const existing = document.querySelector(selector)

    if (!allowed) {
      existing?.remove()
      return
    }
    if (existing) return

    const script = document.createElement('script')
    script.async = true
    script.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + ADSENSE_CLIENT
    script.crossOrigin = 'anonymous'
    script.dataset.shopnoltdAdsense = 'true'
    document.head.appendChild(script)
  }, [allowed])

  return null
}
