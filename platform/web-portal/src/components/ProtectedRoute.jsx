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
      if (active) {
        if (refreshed) {
          try { await platformApi.me(); sessionStorage.setItem('shopno_profile_provisioned', '1') } catch (error) { console.warn('Shopnoltd profile provisioning check failed:', error) }
          setStatus('authenticated')
        } else {
          localStorage.removeItem('shopno_token')
          localStorage.removeItem('shopno_refresh_token')
          setStatus('unauthenticated')
        }
      }
    }

    check()
    return () => { active = false }
  }, [])

  if (status === 'checking') {
    return <main style={{ maxWidth: 720, margin: '60px auto', padding: 24, textAlign: 'center' }}>Checking your Shopnoltd session…</main>
  }

  if (status === 'unauthenticated') {
    const next = `${location.pathname}${location.search}${location.hash}`
    return <Navigate to={`/login?next=${encodeURIComponent(next)}`} replace />
  }

  return children
}
