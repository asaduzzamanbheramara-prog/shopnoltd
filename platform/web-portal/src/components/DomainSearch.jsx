import { useState } from 'react'

const DOMAIN_API =
  import.meta.env.VITE_DOMAIN_API_URL ||
  '/api/v1/domains'

export default function DomainSearch() {
  const [subdomain, setSubdomain] = useState('')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  async function checkAvailability(event) {
    event.preventDefault()

    const value = subdomain.trim().toLowerCase()

    if (!value) {
      setStatus({
        type: 'error',
        message: 'Enter a domain name first.',
      })
      return
    }

    setLoading(true)
    setStatus(null)

    try {
      const response = await fetch(
        `${DOMAIN_API}/check-availability?subdomain=${encodeURIComponent(value)}`
      )

      if (!response.ok) {
        throw new Error('Domain service is unavailable')
      }

      const data = await response.json()

      if (data.available) {
        setStatus({
          type: 'available',
          message: `${data.subdomain} is available!`,
        })
      } else {
        setStatus({
          type: 'taken',
          message: data.reason || 'This domain is unavailable.',
        })
      }
    } catch (error) {
      setStatus({
        type: 'error',
        message: 'Unable to check availability. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  async function registerDomain() {
    const value = subdomain.trim().toLowerCase()
    const token = localStorage.getItem('shopno_token')

    if (!token) {
      sessionStorage.setItem('pending_domain', value)

      window.location.href = `/login?next=/&domain=${encodeURIComponent(value)}`
      return
    }

    setLoading(true)

    try {
      const response = await fetch(DOMAIN_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          subdomain: value,
          target: 'tenant-router.shopnoltd.dpdns.org',
          record_type: 'CNAME',
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Registration failed.')
      }

      setStatus({
        type: 'available',
        message: `${data.subdomain} registered! It may take a few minutes to go live.`,
      })
    } catch (error) {
      setStatus({
        type: 'error',
        message: error.message || 'Unable to register domain. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section
      style={{
        maxWidth: 860,
        margin: '0 auto 60px',
        padding: '38px 28px',
        borderRadius: 20,
        background: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
        color: 'white',
        boxShadow: '0 20px 50px rgba(14,165,233,.25)',
      }}
    >
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>🌐</div>

        <h2
          style={{
            fontSize: 'clamp(28px, 5vw, 42px)',
            margin: '0 0 12px',
          }}
        >
          Register your Shopnoltd domain
        </h2>

        <p
          style={{
            margin: '0 auto 28px',
            maxWidth: 650,
            fontSize: 18,
            lineHeight: 1.6,
            opacity: 0.95,
          }}
        >
          Search for your name and create your own
          <strong> .shopnoltd.dpdns.org </strong>
          address.
        </p>

        <form
          onSubmit={checkAvailability}
          style={{
            display: 'flex',
            gap: 10,
            maxWidth: 680,
            margin: '0 auto',
            flexWrap: 'wrap',
            justifyContent: 'center',
          }}
        >
          <div
            style={{
              display: 'flex',
              flex: '1 1 420px',
              minWidth: 0,
              background: 'white',
              borderRadius: 10,
              overflow: 'hidden',
            }}
          >
            <input
              value={subdomain}
              onChange={(event) =>
                setSubdomain(
                  event.target.value
                    .toLowerCase()
                    .replace(/[^a-z0-9-]/g, '')
                )
              }
              placeholder="yourcompany"
              style={{
                flex: 1,
                border: 'none',
                outline: 'none',
                padding: '16px 18px',
                fontSize: 17,
                minWidth: 0,
              }}
            />

            <span
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: '0 16px',
                color: '#475569',
                background: '#f8fafc',
                fontWeight: 600,
                whiteSpace: 'nowrap',
              }}
            >
              .shopnoltd.dpdns.org
            </span>
          </div>

          <button
            type="submit"
            disabled={loading}
            style={{
              border: 'none',
              borderRadius: 10,
              padding: '16px 22px',
              background: '#0f172a',
              color: 'white',
              fontSize: 16,
              fontWeight: 700,
              cursor: loading ? 'wait' : 'pointer',
            }}
          >
            {loading ? 'Checking...' : 'Check availability'}
          </button>
        </form>

        {status && (
          <div
            style={{
              marginTop: 22,
              padding: 16,
              borderRadius: 10,
              background:
                status.type === 'available'
                  ? 'rgba(34,197,94,.20)'
                  : 'rgba(239,68,68,.20)',
              border:
                status.type === 'available'
                  ? '1px solid rgba(134,239,172,.7)'
                  : '1px solid rgba(252,165,165,.7)',
            }}
          >
            <strong>{status.message}</strong>

            {status.type === 'available' && (
              <div style={{ marginTop: 14 }}>
                <button
                  type="button"
                  onClick={registerDomain}
                  style={{
                    border: 'none',
                    borderRadius: 8,
                    padding: '12px 20px',
                    background: 'white',
                    color: '#0369a1',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  Register this domain →
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
