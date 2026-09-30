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

function consentAllowed() {
  try {
    const value = localStorage.getItem('shopno_analytics_consent')
    return value !== 'denied'
  } catch {
    return true
  }
}

export function setAnalyticsConsent(value) {
  try { localStorage.setItem('shopno_analytics_consent', value ? 'granted' : 'denied') } catch {}
}

export function trackPageView(path = window.location.pathname) {
  if (!consentAllowed()) return
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
