import { API_URL } from '../config'
import { tryRefresh } from './tokenRefresh'

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
    if (detail && typeof detail === 'object' && detail.code) {
      const error = new Error(detail.message || detail.code)
      error.code = detail.code
      error.details = detail
      throw error
    }
    throw new Error(
      `Financial API request failed (${response.status})${detail ? `: ${detail}` : ''}`
    )
  }
  return data
}

export function getFinancialCapabilities() {
  return authenticatedRequest('/api/v1/financial/capabilities')
}

export function getWallet(currency = 'BDT') {
  return authenticatedRequest(`/api/v1/wallet?currency=${encodeURIComponent(currency)}`)
}

export function getWalletLedger(currency = 'BDT', limit = 50) {
  return authenticatedRequest(
    `/api/v1/wallet/ledger?currency=${encodeURIComponent(currency)}&limit=${limit}`
  )
}

export function getTransactions(limit = 50, offset = 0) {
  return authenticatedRequest(`/api/v1/transactions?limit=${limit}&offset=${offset}`).then(
    (data) => (Array.isArray(data) ? data : data?.items || [])
  )
}

export function getPaymentGateways() {
  return authenticatedRequest('/api/v1/billing/gateways')
}

export function createCheckout({
  gateway,
  amount,
  currency,
  reference,
  customer_phone,
}) {
  const numericAmount = Number(amount)
  if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
    return Promise.reject(new Error('Amount must be greater than zero.'))
  }
  if (!gateway || !currency) {
    return Promise.reject(new Error('Gateway and currency are required.'))
  }
  return authenticatedRequest('/api/v1/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({
      gateway: String(gateway).trim().toLowerCase(),
      amount: numericAmount,
      currency: String(currency).trim().toUpperCase(),
      reference,
      customer_phone,
    }),
  })
}

export function getExchangeRates(limit = 100) {
  return authenticatedRequest(`/api/v1/exchange/rates?limit=${limit}`)
}

export function getExchangeRate(from, to) {
  return authenticatedRequest(
    `/api/v1/rate/${encodeURIComponent(String(from).toUpperCase())}/${encodeURIComponent(String(to).toUpperCase())}`
  )
}

export function getExchangeQuote({ from_currency, to_currency, amount }) {
  const numericAmount = Number(amount)
  if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
    return Promise.reject(new Error('Amount must be greater than zero.'))
  }
  return authenticatedRequest('/api/v1/exchange/quote', {
    method: 'POST',
    body: JSON.stringify({
      from_currency: String(from_currency || '').trim().toUpperCase(),
      to_currency: String(to_currency || '').trim().toUpperCase(),
      amount: numericAmount,
    }),
  })
}

export function convertExchange({
  from_currency,
  to_currency,
  amount,
}) {
  const numericAmount = Number(amount)
  if (!Number.isFinite(numericAmount) || numericAmount <= 0) {
    return Promise.reject(new Error('Amount must be greater than zero.'))
  }
  return authenticatedRequest('/api/v1/exchange/convert', {
    method: 'POST',
    body: JSON.stringify({
      from_currency: String(from_currency || '').trim().toUpperCase(),
      to_currency: String(to_currency || '').trim().toUpperCase(),
      amount: numericAmount,
    }),
  })
}
