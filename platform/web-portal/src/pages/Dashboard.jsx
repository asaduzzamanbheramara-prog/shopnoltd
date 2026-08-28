import React, { useEffect, useState } from 'react'
import { API_URL } from '../config'

export default function Dashboard() {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const token = localStorage.getItem('shopno_token')

    if (!token) {
      setLoading(false)
      setError('Please log in.')
      return
    }

    fetch(`${API_URL}/api/v1/users/me`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then(async (response) => {
        if (!response.ok) {
          const text = await response.text()
          throw new Error(
            `Profile request failed (${response.status})${text ? `: ${text}` : ''}`
          )
        }

        return response.json()
      })
      .then((data) => {
        setMe(data)
      })
      .catch((err) => {
        console.error('Dashboard profile request failed:', err)
        setError(err.message)
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  if (loading) {
    return <div style={{ padding: 32 }}>Loading your dashboard…</div>
  }

  if (error) {
    return (
      <div style={{ padding: 32 }}>
        <h2>Dashboard unavailable</h2>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div
      style={{
        maxWidth: 960,
        margin: '0 auto',
        padding: 32,
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Welcome, {me.email || me.id}</h1>
      <p>Tenant: {me.tenant_id || 'default'}</p>
      <p>Roles: {(me.roles || []).join(', ')}</p>
    </div>
  )
}
