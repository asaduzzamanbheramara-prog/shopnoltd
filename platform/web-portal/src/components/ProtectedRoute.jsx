import { Navigate, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { tryRefresh } from '../lib/tokenRefresh'
import { platformApi } from '../lib/platformApi'

function tokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
    return typeof payload.exp === 'number' && payload.exp * 1000 <= Date.now()
  } catch {
    return true
  }
}

export default function ProtectedRoute({ children }) {
  const location = useLocation()
  const [status, setStatus] = useState('checking')

  useEffect(() => {
    let active = true
    let retryTimer = null

    async function check() {
      const token = localStorage.getItem('shopno_token')
      if (!token) {
        if (active) setStatus('unauthenticated')
        return
      }

      if (!tokenExpired(token)) {
        if (sessionStorage.getItem('shopno_profile_provisioned') !== '1') {
          try { await platformApi.me(); sessionStorage.setItem('shopno_profile_provisioned', '1') } catch (error) { console.warn('Shopnoltd profile provisioning check failed:', error) }
        }
        if (active) setStatus('authenticated')
        return
      }

      const refreshed = await tryRefresh()
      if (!active) return
      if (refreshed) {
        try { await platformApi.me(); sessionStorage.setItem('shopno_profile_provisioned', '1') } catch (error) { console.warn('Shopnoltd profile provisioning check failed:', error) }
        if (active) setStatus('authenticated')
        return
      }

      // tryRefresh() preserves credentials on transient network/5xx errors.
      // Do not turn those recoverable failures into a user logout. A revoked
      // or expired refresh token is removed by tryRefresh(); only then should
      // this route clear the remaining access token and require sign-in.
      if (localStorage.getItem('shopno_refresh_token')) {
        setStatus('retrying')
        retryTimer = window.setTimeout(() => {
          if (active) {
            setStatus('checking')
            void check()
          }
        }, 5000)
        return
      }

      localStorage.removeItem('shopno_token')
      localStorage.removeItem('shopno_id_token')
      setStatus('unauthenticated')
    }

    check()
    return () => {
      active = false
      if (retryTimer !== null) window.clearTimeout(retryTimer)
    }
  }, [])

  if (status === 'checking' || status === 'retrying') {
    return <main style={{ maxWidth: 720, margin: '60px auto', padding: 24, textAlign: 'center' }}>
      <h2>{status === 'retrying' ? 'Reconnecting to Shopnoltd…' : 'Checking your Shopnoltd session…'}</h2>
      <p>{status === 'retrying' ? 'A temporary connection issue occurred. Your session is being preserved while we retry securely.' : 'Please wait while we verify your secure session.'}</p>
    </main>
  }

  if (status === 'unauthenticated') {
    const next = `${location.pathname}${location.search}${location.hash}`
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  }

  return children
}
