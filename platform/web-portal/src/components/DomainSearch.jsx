import { useEffect, useState } from 'react'

const DOMAIN_API =
  import.meta.env.VITE_DOMAIN_API_URL ||
  '/api/v1/domains'

const DOMAIN_SUFFIX = '.shopnoltd.dpdns.org'
const MAX_LABEL_LENGTH = 63

function normalizeSubdomain(value) {
  return String(value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '')
    .replace(/^-+/, '')
    .slice(0, MAX_LABEL_LENGTH)
}

function validateSubdomain(value) {
  if (!value) {
    return 'Enter a domain name first.'
  }

  if (value.length < 1 || value.length > MAX_LABEL_LENGTH) {
    return `Domain name must be ${MAX_LABEL_LENGTH} characters or fewer.`
  }

  if (!/^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(value)) {
    return 'Use only letters, numbers, and hyphens. A domain cannot start or end with a hyphen.'
  }

  return null
}

export default function DomainSearch() {
  const [subdomain, setSubdomain] = useState('')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)

  async function checkAvailabilityValue(value) {
    const normalized = normalizeSubdomain(value)
    const validationError = validateSubdomain(normalized)

    if (validationError) {
      setStatus({
        type: 'error',
        message: validationError,
      })
      return
    }

    setSubdomain(normalized)
    setLoading(true)
    setStatus(null)

    try {
      const response = await fetch(
        `${DOMAIN_API}/check-availability?subdomain=${encodeURIComponent(normalized)}`,
        {
          method: 'GET',
          headers: {
            Accept: 'application/json',
          },
        }
      )

      if (!response.ok) {
        throw new Error('Domain service is unavailable')
      }

      const data = await response.json()

      if (data.available) {
        setStatus({
          type: 'available',
          message: `${data.subdomain || normalized} is available!`,
        })
      } else {
        setStatus({
          type: 'taken',
          message: data.reason || 'This domain is unavailable.',
        })
      }
    } catch {
      setStatus({
        type: 'error',
        message: 'Unable to check availability. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const incomingDomain = params.get('domain')

    if (!incomingDomain) {
      return
    }

    const value = normalizeSubdomain(incomingDomain)

    if (!value) {
      return
    }

    setSubdomain(value)
    sessionStorage.removeItem('pending_domain')

    const timer = window.setTimeout(() => {
      checkAvailabilityValue(value)
    }, 0)

    return () => window.clearTimeout(timer)
  }, [])

  async function checkAvailability(event) {
    event.preventDefault()

    const value = normalizeSubdomain(subdomain)
    setSubdomain(value)

    await checkAvailabilityValue(value)
  }

  async function registerDomain() {
    const value = normalizeSubdomain(subdomain)
    const validationError = validateSubdomain(value)

    if (validationError) {
      setStatus({
        type: 'error',
        message: validationError,
      })
      return
    }

    setSubdomain(value)

    const token = localStorage.getItem('shopno_token')

    if (!token) {
      sessionStorage.setItem('pending_domain', value)

      window.location.href =
        `/login?next=/&domain=${encodeURIComponent(value)}`

      return
    }

    setLoading(true)
    setStatus(null)

    try {
      const response = await fetch(DOMAIN_API, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          subdomain: value,
          target: 'tenant-router.shopnoltd.dpdns.org',
          record_type: 'CNAME',
        }),
      })

      let data = {}

      try {
        data = await response.json()
      } catch {
        data = {}
      }

      if (!response.ok) {
        throw new Error(
          data.detail ||
          data.message ||
          'Registration failed.'
        )
      }

      setStatus({
        type: 'available',
        message:
          `${data.subdomain || value} registered! ` +
          'It may take a few minutes to go live.',
      })
    } catch (error) {
      setStatus({
        type: 'error',
        message:
          error.message ||
          'Unable to register domain. Please try again.',
      })
    } finally {
      setLoading(false)
    }
  }

  const inputValue = subdomain
  const canCheck =
    inputValue.length > 0 &&
    !loading

  return (
    <section
      style={{
        width: '100%',
        maxWidth: 860,
        margin: '0 auto 60px',
        padding: 'clamp(22px, 5vw, 38px) clamp(14px, 4vw, 28px)',
        borderRadius: 20,
        boxSizing: 'border-box',
        background: 'linear-gradient(135deg, #0ea5e9, #0369a1)',
        color: 'white',
        boxShadow: '0 20px 50px rgba(14,165,233,.25)',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 760,
          margin: '0 auto',
          textAlign: 'center',
          boxSizing: 'border-box',
        }}
      >
        <div
          aria-hidden="true"
          style={{
            fontSize: 'clamp(38px, 10vw, 48px)',
            lineHeight: 1,
            marginBottom: 10,
          }}
        >
          🌐
        </div>

        <h2
          style={{
            fontSize: 'clamp(26px, 7vw, 42px)',
            lineHeight: 1.15,
            margin: '0 0 12px',
            overflowWrap: 'anywhere',
          }}
        >
          Register your Shopnoltd domain
        </h2>

        <p
          style={{
            margin: '0 auto 28px',
            maxWidth: 650,
            fontSize: 'clamp(15px, 4vw, 18px)',
            lineHeight: 1.6,
            opacity: 0.95,
          }}
        >
          Search for your name and create your own{' '}
          <strong style={{ whiteSpace: 'nowrap' }}>
            {DOMAIN_SUFFIX}
          </strong>{' '}
          address.
        </p>

        <form
          onSubmit={checkAvailability}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
            width: '100%',
            margin: '0 auto',
            boxSizing: 'border-box',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'stretch',
              width: '100%',
              minWidth: 0,
              background: 'white',
              borderRadius: 12,
              overflow: 'hidden',
              boxSizing: 'border-box',
              boxShadow: '0 4px 14px rgba(15,23,42,.12)',
            }}
          >
            <input
              id="shopnoltd-domain-input"
              name="subdomain"
              type="text"
              value={inputValue}
              onChange={(event) => {
                // Keep typing natural on Android/iOS/desktop.
                // Normalization happens on blur/submit instead of
                // aggressively deleting characters during typing.
                setSubdomain(event.target.value)

                if (status) {
                  setStatus(null)
                }
              }}
              onBlur={() => {
                setSubdomain(normalizeSubdomain(subdomain))
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.currentTarget.form?.requestSubmit()
                }
              }}
              placeholder="yourcompany"
              aria-label="Shopnoltd domain name"
              autoComplete="off"
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              inputMode="text"
              enterKeyHint="search"
              maxLength={MAX_LABEL_LENGTH}
              style={{
                flex: '1 1 auto',
                width: '100%',
                minWidth: 0,
                height: 54,
                border: 'none',
                outline: 'none',
                padding: '14px 16px',
                margin: 0,
                boxSizing: 'border-box',
                fontSize: '16px',
                lineHeight: 1.4,
                color: '#0f172a',
                background: 'white',
                WebkitAppearance: 'none',
                appearance: 'none',
              }}
            />

            <span
              style={{
                flex: '0 0 auto',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 10px',
                minWidth: 0,
                maxWidth: '42%',
                color: '#475569',
                background: '#f8fafc',
                borderLeft: '1px solid #e2e8f0',
                fontSize: 'clamp(11px, 3vw, 15px)',
                fontWeight: 600,
                lineHeight: 1.2,
                whiteSpace: 'normal',
                overflowWrap: 'anywhere',
                wordBreak: 'break-word',
                textAlign: 'center',
                boxSizing: 'border-box',
              }}
            >
              {DOMAIN_SUFFIX}
            </span>
          </div>

          <button
            type="submit"
            disabled={!canCheck}
            style={{
              width: '100%',
              minHeight: 54,
              border: 'none',
              borderRadius: 12,
              padding: '14px 20px',
              boxSizing: 'border-box',
              background: loading ? '#334155' : '#0f172a',
              color: 'white',
              fontSize: 16,
              lineHeight: 1.3,
              fontWeight: 700,
              cursor: loading ? 'wait' : 'pointer',
              touchAction: 'manipulation',
              WebkitTapHighlightColor: 'transparent',
            }}
          >
            {loading ? 'Checking...' : 'Check availability'}
          </button>
        </form>

        {status && (
          <div
            role="status"
            aria-live="polite"
            style={{
              marginTop: 22,
              padding: 16,
              borderRadius: 12,
              background:
                status.type === 'available'
                  ? 'rgba(34,197,94,.20)'
                  : status.type === 'taken'
                    ? 'rgba(251,191,36,.20)'
                    : 'rgba(248,113,113,.20)',
              border: '1px solid rgba(255,255,255,.18)',
              boxSizing: 'border-box',
              overflowWrap: 'anywhere',
              lineHeight: 1.5,
            }}
          >
            {status.message}

            {status.type === 'available' && (
              <button
                type="button"
                onClick={registerDomain}
                disabled={loading}
                style={{
                  display: 'block',
                  width: '100%',
                  maxWidth: 420,
                  minHeight: 52,
                  margin: '14px auto 0',
                  border: 'none',
                  borderRadius: 10,
                  padding: '13px 18px',
                  boxSizing: 'border-box',
                  background: 'white',
                  color: '#0369a1',
                  fontSize: 16,
                  fontWeight: 700,
                  cursor: loading ? 'wait' : 'pointer',
                  touchAction: 'manipulation',
                  WebkitTapHighlightColor: 'transparent',
                }}
              >
                Register this domain →
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
