import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KEYCLOAK_CLIENT_ID, KEYCLOAK_REALM, KEYCLOAK_URL, REDIRECT_URI } from '../config'
import { platformApi } from '../lib/platformApi'

export default function Callback() {
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const returnedState = params.get('state')
    const oauthError = params.get('error')
    const oauthErrorDescription = params.get('error_description')
    const verifier = sessionStorage.getItem('pkce_verifier')
    const expectedState = sessionStorage.getItem('oidc_state')

    if (oauthError) {
      setError(oauthErrorDescription || oauthError)
      sessionStorage.removeItem('pkce_verifier')
      sessionStorage.removeItem('oidc_state')
      return
    }
    if (!code || !verifier || !expectedState || returnedState !== expectedState) {
      setError('Authentication state validation failed. Please try again.')
      sessionStorage.removeItem('pkce_verifier')
      sessionStorage.removeItem('oidc_state')
      return
    }

    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: KEYCLOAK_CLIENT_ID,
      code,
      redirect_uri: REDIRECT_URI,
      code_verifier: verifier,
    })

    fetch(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    })
      .then(async (response) => {
        const data = await response.json()
        if (!response.ok || !data.access_token) throw new Error(data.error_description || data.error || 'Authentication failed.')
        return data
      })
      .then((data) => {
        // Persist the verified OIDC tokens before any optional API work. A slow or
        // unavailable profile/referral endpoint must never strand the user on
        // "Completing sign in…" after Keycloak has successfully authenticated them.
        localStorage.setItem('shopno_token', data.access_token)
        if (data.refresh_token) localStorage.setItem('shopno_refresh_token', data.refresh_token)

        const pendingReferral = sessionStorage.getItem('pending_referral_code')
        const pendingReferralCategory = sessionStorage.getItem('pending_referral_category')
        const pendingDomain = sessionStorage.getItem('pending_domain')
        const next = sessionStorage.getItem('post_login_next')

        sessionStorage.removeItem('pkce_verifier')
        sessionStorage.removeItem('oidc_state')
        sessionStorage.removeItem('pending_domain')
        sessionStorage.removeItem('pending_referral_code')
        sessionStorage.removeItem('pending_referral_category')
        sessionStorage.removeItem('post_login_next')

        // Profile and referral initialization are ancillary to OIDC token exchange.
        // Run them in the background so network/API latency cannot block navigation.
        void (async () => {
          try {
            await platformApi.me()
            sessionStorage.setItem('shopno_profile_provisioned', '1')
          } catch (profileError) {
            console.warn('Shopnoltd profile provisioning check failed after login:', profileError)
          }

          if (pendingReferral) {
            try {
              await platformApi.claimReferral(pendingReferral, pendingReferralCategory)
            } catch (referralError) {
              console.warn('Referral attribution could not be claimed:', referralError)
            }
          }

          // If no direct referral was supplied, the API preserves legacy/direct attribution or binds Admin Office as the fallback.
          try {
            await platformApi.referralMe()
          } catch (referralError) {
            console.warn('Referral attribution initialization skipped:', referralError)
          }
        })()

        if (pendingDomain) {
          navigate(`/?domain=${encodeURIComponent(pendingDomain)}`, { replace: true })
        } else if (next && next.startsWith('/') && !next.startsWith('//')) {
          navigate(next, { replace: true })
        } else {
          navigate('/dashboard', { replace: true })
        }
      })
      .catch((err) => setError(err.message))
  }, [navigate])

  if (error) return <div style={{ maxWidth: 640, margin: '80px auto', padding: 24 }}><h2>Authentication failed</h2><p>{error}</p><a href="/login">Return to login</a></div>
  return <div style={{ maxWidth: 640, margin: '80px auto', padding: 24, textAlign: 'center' }}>Completing sign in…</div>
}
