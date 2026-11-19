import { useEffect, useState } from 'react'
import { getConsentPreferences, hasAdvertisingConsent } from './analytics'

export function useAdvertisingConsent() {
  const [allowed, setAllowed] = useState(hasAdvertisingConsent)

  useEffect(() => {
    const refresh = () => setAllowed(hasAdvertisingConsent())
    window.addEventListener('shopno:consent-updated', refresh)
    return () => window.removeEventListener('shopno:consent-updated', refresh)
  }, [])

  return allowed
}

export function useGoogleTagConsent() {
  const [allowed, setAllowed] = useState(() => {
    const preferences = getConsentPreferences()
    return preferences?.analytics === true || preferences?.advertising === true
  })

  useEffect(() => {
    const refresh = () => {
      const preferences = getConsentPreferences()
      setAllowed(preferences?.analytics === true || preferences?.advertising === true)
    }
    window.addEventListener('shopno:consent-updated', refresh)
    return () => window.removeEventListener('shopno:consent-updated', refresh)
  }, [])

  return allowed
}
