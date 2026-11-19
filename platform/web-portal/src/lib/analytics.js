const VISITOR_KEY = 'shopno_visitor_id_v1'

function visitorId() {
  try {
    let id = localStorage.getItem(VISITOR_KEY)
    if (!id) {
      id = crypto.randomUUID()
      localStorage.setItem(VISITOR_KEY, id)
    }
    return id
  } catch {
    return 'ephemeral-' + Math.random().toString(36).slice(2)
  }
}

function deviceCategory() {
  const w = window.innerWidth || 1024
  if (w < 768) return 'mobile'
  if (w < 1024) return 'tablet'
  return 'desktop'
}

function browserName() {
  const ua = navigator.userAgent || ''
  if (/Edg\//.test(ua)) return 'Edge'
  if (/Chrome\//.test(ua) && !/Edg\//.test(ua)) return 'Chrome'
  if (/Firefox\//.test(ua)) return 'Firefox'
  if (/Safari\//.test(ua) && !/Chrome\//.test(ua)) return 'Safari'
  return 'Other'
}

function osName() {
  const ua = navigator.userAgent || ''
  if (/Android/i.test(ua)) return 'Android'
  if (/iPhone|iPad|iPod/i.test(ua)) return 'iOS'
  if (/Windows/i.test(ua)) return 'Windows'
  if (/Mac OS X/i.test(ua)) return 'macOS'
  if (/Linux/i.test(ua)) return 'Linux'
  return 'Other'
}

const CONSENT_KEY = 'shopno_consent_preferences'

export function getConsentPreferences() {
  try {
    const raw = localStorage.getItem(CONSENT_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    return {
      analytics: parsed?.analytics === true,
      advertising: parsed?.advertising === true,
    }
  } catch {
    return null
  }
}

function consentAllowed() {
  return getConsentPreferences()?.analytics === true
}

export function hasAdvertisingConsent() {
  return getConsentPreferences()?.advertising === true
}

export function ensureGoogleAnalyticsConfigured() {
  if (typeof window.gtag !== 'function' || window.__shopnoltdGaConfigured) return
  window.gtag('config', 'G-JMMVDQQ08Z', { send_page_view: false })
  window.__shopnoltdGaConfigured = true
}

export function setConsentPreferences(preferences = {}) {
  const normalized = {
    analytics: preferences.analytics === true,
    advertising: preferences.advertising === true,
  }

  try {
    localStorage.setItem(CONSENT_KEY, JSON.stringify(normalized))
    localStorage.setItem('shopno_analytics_consent', normalized.analytics ? 'granted' : 'denied')
  } catch {}

  if (typeof window.gtag === 'function') {
    const granted = value => value ? 'granted' : 'denied'
    window.gtag('consent', 'update', {
      analytics_storage: granted(normalized.analytics),
      ad_storage: granted(normalized.advertising),
      ad_user_data: granted(normalized.advertising),
      ad_personalization: granted(normalized.advertising),
    })
  }

  if (normalized.analytics) ensureGoogleAnalyticsConfigured()
  window.dispatchEvent(new Event('shopno:consent-updated'))
  if (normalized.analytics) trackPageView(window.location.pathname + window.location.search)
}

export function setAnalyticsConsent(value) {
  const current = getConsentPreferences() || { analytics: false, advertising: false }
  setConsentPreferences({ ...current, analytics: Boolean(value) })
}


const SAFE_EVENT_PARAM_KEYS = new Set([
  'method', 'currency', 'value', 'transaction_id', 'items', 'item_id', 'item_name', 'item_category',
  'quantity', 'coupon', 'shipping', 'tax', 'payment_type', 'content_type',
  'content_id', 'search_term', 'years',
])

function safeEventParams(params = {}) {
  const output = {}
  for (const [key, value] of Object.entries(params || {})) {
    if (!SAFE_EVENT_PARAM_KEYS.has(key)) continue
    if (key === 'items' && Array.isArray(value)) {
      output.items = value.slice(0, 10).map(item => {
        const safe = {}
        for (const [itemKey, itemValue] of Object.entries(item || {})) {
          if (!['item_id', 'item_name', 'item_category', 'quantity', 'price'].includes(itemKey)) continue
          if (typeof itemValue === 'string' || (typeof itemValue === 'number' && Number.isFinite(itemValue))) safe[itemKey] = itemValue
        }
        return safe
      })
      continue
    }
    if (typeof value === 'string' && value.length <= 100) output[key] = value
    else if (typeof value === 'number' && Number.isFinite(value)) output[key] = value
  }
  return output
}

export function trackEvent(name, params = {}, options = {}) {
  if (!consentAllowed() || typeof window.gtag !== 'function') return false
  if (!/^[a-z][a-z0-9_]{0,39}$/.test(String(name))) return false

  const dedupeKey = options?.dedupeKey
  if (dedupeKey) {
    const storageKey = 'shopno_ga_event_' + name + '_' + String(dedupeKey).slice(0, 100)
    try {
      if (sessionStorage.getItem(storageKey)) return false
      sessionStorage.setItem(storageKey, '1')
    } catch {}
  }

  ensureGoogleAnalyticsConfigured()
  window.gtag('event', name, safeEventParams(params))
  return true
}

export function trackPageView(path = window.location.pathname) {
  if (!consentAllowed()) return
  // Configure only after explicit analytics consent; React Router owns page_view events.
  ensureGoogleAnalyticsConfigured()
  if (typeof window.gtag === 'function') {
    window.gtag('event', 'page_view', { page_path: path, page_location: window.location.href, page_title: document.title || 'Shopnoltd' })
  }
  const url = new URL(window.location.href)
  const properties = {
    visitor_id: visitorId(),
    page_path: path,
    page_title: document.title || 'Shopnoltd',
    landing_page: sessionStorage.getItem('shopno_landing_page') || path,
    referrer: document.referrer || 'direct',
    utm_source: url.searchParams.get('utm_source') || undefined,
    utm_medium: url.searchParams.get('utm_medium') || undefined,
    utm_campaign: url.searchParams.get('utm_campaign') || undefined,
    language: navigator.language || 'unknown',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'unknown',
    device_category: deviceCategory(),
    browser: browserName(),
    os: osName(),
    screen_category: `${window.screen?.width || 0}x${window.screen?.height || 0}`,
    logged_in: !!localStorage.getItem('shopno_token'),
  }
  if (!sessionStorage.getItem('shopno_landing_page')) {
    try { sessionStorage.setItem('shopno_landing_page', path) } catch {}
  }
  const payload = JSON.stringify({ name: 'page_view', properties, source: 'web-portal' })
  try {
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/v1/analytics/collect', new Blob([payload], { type: 'application/json' }))
      return
    }
  } catch {}
  fetch('/api/v1/analytics/collect', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload, keepalive: true }).catch(() => {})
}
