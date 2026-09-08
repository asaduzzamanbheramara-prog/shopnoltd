import { tryRefresh } from './tokenRefresh'

// payment-service lives on its own host — this was previously defaulting
// to API_URL (api.shopnoltd.dpdns.org), which routes to the AI-platform
// backend and has none of these routes. Matches the pattern
// AdminDashboard.jsx already uses for the same service.
const PAYMENT_API_URL =
  import.meta.env.VITE_PAYMENT_API_URL || 'https://payment-service.shopnoltd.dpdns.org'

function token() {
  return localStorage.getItem('shopno_token')
}

export async function authenticatedRequest(path, options = {}) {
  const jwt = token()
  if (!jwt) {
    throw new Error('Authentication required. Please log in.')
  }
  const headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${jwt}`,
    ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(options.headers || {}),
  }
  const response = await fetch(`${PAYMENT_API_URL}${path}`, {
    ...options,
    headers,
  })
  const text = await response.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = text
    }
  }

  if (response.status === 401 && !options._retried) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      return authenticatedRequest(path, { ...options, _retried: true })
    }
    localStorage.removeItem('shopno_token')
    throw new Error('Your session has expired. Please log in again.')
  }
  if (!response.ok) {
    const detail =
      typeof data === 'object' && data !== null
        ? data.detail || data.message || JSON.stringify(data)
        : data
    throw new Error(
      `Financial API request failed (${response.status})${detail ? `: ${detail}` : ''}`
    )
  }
  return data
}

// --- Wallet ---------------------------------------------------------------
// Path param, plural, matches app/api/wallets.py. Backend now
// auto-provisions a zero-balance wallet on first access instead of 404ing.
export function getWallet(currency = 'BDT') {
  return authenticatedRequest(`/api/v1/wallets/${encodeURIComponent(currency.toUpperCase())}`)
}
export function getWalletLedger(currency = 'BDT', limit = 50) {
  return authenticatedRequest(
    `/api/v1/wallets/${encodeURIComponent(currency.toUpperCase())}/ledger?limit=${limit}`
  )
}

// --- Transactions ----------------------------------------------------------
export function getTransactions() {
  return authenticatedRequest('/api/v1/transactions')
}

// --- Gateways / checkout ----------------------------------------------------
// GET /api/v1/billing/gateways now returns the real, live provider list
// (see backend app/api/methods.py) instead of the old fallback that only
// ever showed "stripe".
export function getPaymentGateways() {
  return authenticatedRequest('/api/v1/billing/gateways')
}

// There's no separate "billing/checkout" endpoint on the backend — the
// real, working, multi-provider flow is POST /api/v1/deposits. This maps
// the checkout form's fields onto that contract instead of a fictional one.
export function createCheckout({ gateway, amount, currency, reference, customer_phone }) {
  return authenticatedRequest('/api/v1/deposits', {
    method: 'POST',
    body: JSON.stringify({
      method: gateway,
      amount: Number(amount),
      currency,
      return_url: `${window.location.origin}/checkout/complete?ref=${encodeURIComponent(
        reference || ''
      )}`,
      metadata: customer_phone ? { phone: customer_phone, reference } : { reference },
    }),
  })
}

// --- Exchange ----------------------------------------------------------------
// Backend mounts exchanges.py under /api/v1/exchanges, with query params
// from_currency/to_currency (not /api/v1/rate/{from}/{to}).
export function getExchangeRate(from, to) {
  return authenticatedRequest(
    `/api/v1/exchanges/rate?from_currency=${encodeURIComponent(from)}&to_currency=${encodeURIComponent(to)}`
  )
}
export function convertExchange({ from_currency, to_currency, amount }) {
  return authenticatedRequest('/api/v1/exchanges/convert', {
    method: 'POST',
    body: JSON.stringify({
      from_currency,
      to_currency,
      amount: Number(amount),
    }),
  })
}
