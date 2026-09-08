import { tryRefresh } from './tokenRefresh'

const API_URL = 'https://payment-service.shopnoltd.dpdns.org'

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
  const response = await fetch(`${API_URL}${path}`, {
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

export function getWallet(currency = 'BDT') {
  return authenticatedRequest(`/api/v1/wallets/${encodeURIComponent(currency)}`)
}
export function getWalletLedger(currency = 'BDT', limit = 50) {
  return authenticatedRequest(
    `/api/v1/wallets/${encodeURIComponent(currency)}/ledger?limit=${limit}`
  )
}
export function getTransactions() {
  return authenticatedRequest('/api/v1/transactions')
}
export function getPaymentGateways() {
  return authenticatedRequest('/api/v1/methods')
}
export function createCheckout({ gateway, amount, currency, reference, customer_phone }) {
  return authenticatedRequest('/api/v1/deposits', {
    method: 'POST',
    body: JSON.stringify({
      method: gateway,
      amount: Number(amount),
      currency,
      reference,
      customer_phone,
    }),
  })
}
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
