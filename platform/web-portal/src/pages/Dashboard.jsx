import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { API_URL } from '../config'
import { SERVICES, ADMIN_SERVICES } from '../data/serviceCatalog'
import { isPlatformAdmin } from '../lib/jwt'

function QuickLink({ service }) {
  const isInternal = service.url.startsWith('/')
  return (
    <a
      href={service.url}
      target={isInternal ? undefined : '_blank'}
      rel={isInternal ? undefined : 'noopener noreferrer'}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        textDecoration: 'none',
        color: 'inherit',
        padding: '14px 16px',
        background: 'white',
        border: '1px solid #e2e8f0',
        borderRadius: 10,
      }}
    >
      <span style={{ fontSize: 22 }}>{service.icon}</span>
      <span style={{ fontWeight: 600, color: '#0f172a' }}>{service.name}</span>
    </a>
  )
}

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

  const isAdmin = isPlatformAdmin()

  return (
    <div
      style={{
        maxWidth: 1180,
        margin: '0 auto',
        padding: 'clamp(28px, 6vw, 48px) clamp(14px, 4vw, 24px) 80px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>Welcome, {me.email || me.id}</h1>
      <p style={{ color: '#64748b' }}>
        Tenant: {me.tenant_id || 'default'} · Roles: {(me.roles || []).join(', ') || 'customer'}
      </p>

      {isAdmin && (
        <Link
          to="/admin"
          style={{
            display: 'inline-block',
            marginTop: 12,
            marginBottom: 8,
            padding: '10px 16px',
            borderRadius: 8,
            background: '#0ea5e9',
            color: 'white',
            fontWeight: 600,
            textDecoration: 'none',
          }}
        >
          Open Admin Dashboard →
        </Link>
      )}

      <section style={{ marginTop: 40 }}>
        <h2>Your services</h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: 12,
          marginTop: 14,
        }}>
          {SERVICES.map((service) => (
            <QuickLink key={service.name} service={service} />
          ))}
        </div>
      </section>

      {isAdmin && (
        <section style={{ marginTop: 40 }}>
          <h2>Administration</h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12,
            marginTop: 14,
          }}>
            {ADMIN_SERVICES.map((service) => (
              <QuickLink key={service.name} service={service} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
