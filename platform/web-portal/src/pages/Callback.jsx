import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { KEYCLOAK_URL, KEYCLOAK_REALM, KEYCLOAK_CLIENT_ID, REDIRECT_URI } from '../config'

export default function Callback() {
  const [error, setError] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get('code')
    const verifier = sessionStorage.getItem('pkce_verifier')
    if (!code || !verifier) {
      setError('Missing login code or verifier -- please try signing in again.')
      return
    }
    fetch(`${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: KEYCLOAK_CLIENT_ID,
        code,
        redirect_uri: REDIRECT_URI,
        code_verifier: verifier,
      }),
    })
      .then(r => r.json())
      .then(d => {
        if (!d.access_token) { setError(d.error_description || 'Login failed.'); return }
        localStorage.setItem('shopno_token', d.access_token)
        sessionStorage.removeItem('pkce_verifier')
        navigate('/dashboard')
      })
      .catch(e => setError(e.message))
  }, [navigate])

  return (
    <div style={{ padding: 64, textAlign: 'center' }}>
      {error ? <p style={{ color: '#ef4444' }}>{error}</p> : <p>Signing you in…</p>}
    </div>
  )
}
