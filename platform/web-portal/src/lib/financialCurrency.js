import { useEffect, useState } from 'react'

export const DEFAULT_FINANCIAL_CURRENCY = 'USD'
const STORAGE_KEY = 'shopnoltd_financial_currency'
const CHANGE_EVENT = 'shopnoltd:financial-currency-change'

const allowedCurrency = (value) => /^[A-Z]{3}$/.test(String(value || '').toUpperCase())

export function getPreferredFinancialCurrency() {
  if (typeof window === 'undefined') return DEFAULT_FINANCIAL_CURRENCY
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY)
    return allowedCurrency(saved) ? saved.toUpperCase() : DEFAULT_FINANCIAL_CURRENCY
  } catch {
    return DEFAULT_FINANCIAL_CURRENCY
  }
}

export function setPreferredFinancialCurrency(value) {
  const currency = String(value || '').trim().toUpperCase()
  if (!allowedCurrency(currency)) return
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(STORAGE_KEY, currency)
  } catch {
    // Keep the in-memory selection usable when browser storage is unavailable.
  }
  window.dispatchEvent(new Event(CHANGE_EVENT))
}

export function useFinancialCurrency() {
  const [currency, setCurrency] = useState(getPreferredFinancialCurrency)

  useEffect(() => {
    const sync = () => setCurrency(getPreferredFinancialCurrency())
    window.addEventListener(CHANGE_EVENT, sync)
    window.addEventListener('storage', sync)
    return () => {
      window.removeEventListener(CHANGE_EVENT, sync)
      window.removeEventListener('storage', sync)
    }
  }, [])

  return [currency, setPreferredFinancialCurrency]
}

export function formatFinancialAmount(value, currency = DEFAULT_FINANCIAL_CURRENCY, locale) {
  const amount = Number(value)
  if (!Number.isFinite(amount)) return '—'
  const code = allowedCurrency(currency) ? String(currency).toUpperCase() : DEFAULT_FINANCIAL_CURRENCY
  try {
    return new Intl.NumberFormat(locale, {
      style: 'currency',
      currency: code,
      maximumFractionDigits: 2,
    }).format(amount)
  } catch {
    return `${amount.toFixed(2)} ${code}`
  }
}
