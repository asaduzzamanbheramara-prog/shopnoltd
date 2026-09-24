import { tryRefresh } from './tokenRefresh'
import { decodeToken } from './jwt'

// Keep browser financial traffic on the unified API origin. The API service
// proxies to payment-service internally, so payment/exchange hosts are never
// exposed as browser dependencies.
const FINANCIAL_API_URL =
  import.meta.env.VITE_API_URL ||
  import.meta.env.VITE_API_BASE_URL ||
  'https://api.shopnoltd.dpdns.org'

const TOKEN_EXPIRY_BUFFER_SECONDS = 60

function token() {
  return localStorage.getItem('shopno_token')
}

function tokenNeedsRefresh(jwt) {
  if (!jwt) return true

  const payload = decodeToken(jwt)
  if (!payload || typeof payload.exp !== 'number') {
    // Do not reject opaque/non-JWT tokens here. Let the API validate them.
    return false
  }

  const now = Math.floor(Date.now() / 1000)
  return payload.exp <= now + TOKEN_EXPIRY_BUFFER_SECONDS
}

async function getFreshToken() {
  let jwt = token()

  if (!jwt) {
    throw new Error('Authentication required. Please log in.')
  }

  if (tokenNeedsRefresh(jwt)) {
    const refreshed = await tryRefresh()
    if (refreshed) jwt = refreshed
  }

  return jwt
}

export async function authenticatedRequest(path, options = {}) {
  const { _retried, ...requestOptions } = options
  let jwt = await getFreshToken()

  let headers = {
    Accept: 'application/json',
    Authorization: `Bearer ${jwt}`,
    ...(requestOptions.body ? { 'Content-Type': 'application/json' } : {}),
    ...(requestOptions.headers || {}),
  }

  let response = await fetch(`${FINANCIAL_API_URL}${path}`, {
    ...requestOptions,
    headers,
  })

  let text = await response.text()
  let data = null

  if (text) {
    try { data = JSON.parse(text) } catch { data = text }
  }

  // A token can expire between the pre-flight check and the actual request.
  // Refresh once and retry once. Never recurse indefinitely.
  if (response.status === 401 && !_retried) {
    const refreshed = await tryRefresh()

    if (refreshed) {
      jwt = refreshed
      headers = {
        Accept: 'application/json',
        Authorization: `Bearer ${jwt}`,
        ...(requestOptions.body ? { 'Content-Type': 'application/json' } : {}),
        ...(requestOptions.headers || {}),
      }

      response = await fetch(`${FINANCIAL_API_URL}${path}`, {
        ...requestOptions,
        headers,
      })

      text = await response.text()
      data = null

      if (text) {
        try { data = JSON.parse(text) } catch { data = text }
      }
    } else {
      localStorage.removeItem('shopno_token')
      localStorage.removeItem('shopno_refresh_token')
      throw new Error('Your session has expired. Please log in again.')
    }
  }

  if (response.status === 401) {
    localStorage.removeItem('shopno_token')
    localStorage.removeItem('shopno_refresh_token')
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

export function getWallet(currency = 'BDT') {
  return authenticatedRequest(`/api/v1/wallets/${encodeURIComponent(currency.toUpperCase())}`)
}

export function getWalletLedger(currency = 'BDT', limit = 50) {
  const boundedLimit = Math.min(Math.max(Number(limit) || 50, 1), 200)
  return authenticatedRequest(`/api/v1/wallets/${encodeURIComponent(currency.toUpperCase())}/ledger?limit=${boundedLimit}`)
}

export function getTransactions(limit = 50, offset = 0) {
  const boundedLimit = Math.min(Math.max(Number(limit) || 50, 1), 200)
  const boundedOffset = Math.max(Number(offset) || 0, 0)
  return authenticatedRequest(`/api/v1/transactions?limit=${boundedLimit}&offset=${boundedOffset}`)
}

export function getPaymentGateways() {
  return authenticatedRequest('/api/v1/billing/gateways')
}

export function createCheckout({ gateway, amount, currency, reference, customer_phone, customer_email, customer_name, idempotency_key }) {
  const key = idempotency_key || (reference ? `checkout:${String(reference).slice(0, 112)}` : crypto.randomUUID())
  return authenticatedRequest('/api/v1/deposits', {
    method: 'POST',
    body: JSON.stringify({
      method: gateway, amount: Number(amount), currency: String(currency).toUpperCase(), idempotency_key: key,
      return_url: `${window.location.origin}/checkout/complete?ref=${encodeURIComponent(reference || '')}`,
      metadata: {
        reference,
        customer_phone: customer_phone || undefined,
        customer_email: customer_email || undefined,
        customer_name: customer_name || undefined,
      },
    }),
  })
}

export function getDirectPaymentAccounts(provider) {
  const suffix = provider ? `?provider=${encodeURIComponent(String(provider).toLowerCase())}` : ''
  return authenticatedRequest(`/api/v1/direct-payments/accounts${suffix}`)
}

export function createDirectPaymentIntent({ provider, amount, currency = 'BDT', account_id, order_id }) {
  return authenticatedRequest('/api/v1/direct-payments/intents', {
    method: 'POST',
    body: JSON.stringify({ provider: String(provider).toLowerCase(), amount: Number(amount), currency: String(currency).toUpperCase(), account_id, order_id }),
  })
}

export function submitDirectPayment({ intent_id, txid, sender_number, amount, reference }) {
  return authenticatedRequest(`/api/v1/direct-payments/intents/${encodeURIComponent(intent_id)}/submit`, {
    method: 'POST',
    body: JSON.stringify({ txid, sender_number, amount: amount == null ? undefined : Number(amount), reference }),
  })
}

export function getDirectPaymentIntent(intent_id) {
  return authenticatedRequest(`/api/v1/direct-payments/intents/${encodeURIComponent(intent_id)}`)
}

export function getExchangeRate(from, to) {
  return authenticatedRequest(`/api/v1/exchanges/rate?from_currency=${encodeURIComponent(String(from).toUpperCase())}&to_currency=${encodeURIComponent(String(to).toUpperCase())}`)
}

export function convertExchange({ from_currency, to_currency, amount, idempotency_key }) {
  const key = idempotency_key || crypto.randomUUID()
  return authenticatedRequest('/api/v1/exchanges/convert', {
    method: 'POST',
    body: JSON.stringify({ from_currency: String(from_currency).toUpperCase(), to_currency: String(to_currency).toUpperCase(), amount: Number(amount), idempotency_key: key }),
  })
}
