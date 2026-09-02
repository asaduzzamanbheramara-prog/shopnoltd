import { API_URL } from '../config'

function token() {
  return localStorage.getItem('shopno_token')
}

async function request(path, options = {}) {
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

  if (response.status === 401) {
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
  return request(`/api/v1/wallet?currency=${encodeURIComponent(currency)}`)
}

export function getWalletLedger(currency = 'BDT', limit = 50) {
  return request(
    `/api/v1/wallet/ledger?currency=${encodeURIComponent(currency)}&limit=${limit}`
  )
}

export function getTransactions() {
  return request('/api/v1/transactions')
}

export function getPaymentGateways() {
  return request('/api/v1/billing/gateways')
}

export function createCheckout({
  gateway,
  amount,
  currency,
  reference,
  customer_phone,
}) {
  return request('/api/v1/billing/checkout', {
    method: 'POST',
    body: JSON.stringify({
      gateway,
      amount: Number(amount),
      currency,
      reference,
      customer_phone,
    }),
  })
}

export function getExchangeRate(from, to) {
  return request(
    `/api/v1/rate/${encodeURIComponent(from)}/${encodeURIComponent(to)}`
  )
}

export function convertExchange({
  from_currency,
  to_currency,
  amount,
}) {
  return request('/api/v1/exchange/convert', {
    method: 'POST',
    body: JSON.stringify({
      from_currency,
      to_currency,
      amount: Number(amount),
    }),
  })
}
