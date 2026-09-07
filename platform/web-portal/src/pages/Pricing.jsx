import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getExchangeQuote } from '../lib/financialApi'

const plans = [
  { name: 'Free', price: 0, features: ['1 user', '1 GB storage', 'Community support'] },
  { name: 'Starter', price: 9, features: ['5 users', '50 GB storage', 'Email support'] },
  { name: 'Pro', price: 29, features: ['25 users', '500 GB storage', 'Priority support'] },
  { name: 'Business', price: 99, features: ['100 users', '5 TB storage', '24/7 support'] },
  { name: 'Enterprise', price: 299, features: ['Unlimited users', 'Unlimited storage', 'Dedicated success manager'] },
]

const CURRENCY_SYMBOLS = {
  USD: '$',
  BDT: '৳',
  EUR: '€',
  GBP: '£',
  INR: '₹',
  AUD: 'A$',
  CAD: 'C$',
  SGD: 'S$',
}

export default function Pricing() {
  const navigate = useNavigate()
  const [currency, setCurrency] = useState('USD')
  const [converted, setConverted] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (currency === 'USD') {
      setConverted(Object.fromEntries(plans.map((plan) => [plan.name, plan.price])))
      setError(null)
      return
    }

    let active = true
    setLoading(true)
    setError(null)

    Promise.all(
      plans.map(async (plan) => {
        if (plan.price === 0) return [plan.name, 0]
        const quote = await getExchangeQuote({
          from_currency: 'USD',
          to_currency: currency,
          amount: plan.price,
        })
        const amount = Number(quote?.to_amount ?? quote?.converted_amount ?? quote?.amount)
        if (!Number.isFinite(amount)) {
          throw new Error(`Invalid exchange quote for ${currency}.`)
        }
        return [plan.name, amount]
      })
    )
      .then((entries) => {
        if (active) setConverted(Object.fromEntries(entries))
      })
      .catch((err) => {
        if (active) {
          setConverted({})
          setError(err.message || 'Unable to load the current exchange rate.')
        }
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [currency])

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', alignItems: 'end', marginBottom: 24 }}>
        <div>
          <h1 style={{ marginBottom: 8 }}>ShopnoltdToolbox Pricing</h1>
          <p style={{ margin: 0, color: '#64748b' }}>
            All Shopnoltd services use the same billing, payment and exchange foundation.
          </p>
        </div>
        <label>
          Currency
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            style={{ display: 'block', marginTop: 5, padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }}
          >
            {Object.keys(CURRENCY_SYMBOLS).map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
        </label>
      </div>

      {error && (
        <div style={{ marginBottom: 16, padding: 12, borderRadius: 8, background: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' }}>
          {error} Sign in to view live converted pricing, or keep USD as the pricing base.
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {plans.map((plan) => {
          const amount = converted[plan.name]
          const hasAmount = Number.isFinite(Number(amount))
          return (
            <div key={plan.name} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
              <h2>{plan.name}</h2>
              <p style={{ fontSize: 36, fontWeight: 700 }}>
                {hasAmount ? `${CURRENCY_SYMBOLS[currency] || currency} ${Number(amount).toFixed(2)}` : '—'}
                <span style={{ fontSize: 14, color: '#64748b' }}>/mo</span>
              </p>
              {currency !== 'USD' && hasAmount && (
                <p style={{ marginTop: -12, color: '#64748b', fontSize: 13 }}>
                  Base price: ${plan.price.toFixed(2)} USD · live exchange quote
                </p>
              )}
              <ul>{plan.features.map((feature) => <li key={feature}>{feature}</li>)}</ul>
              <button
                disabled={loading || (plan.price > 0 && !hasAmount)}
                onClick={() => navigate(`/checkout?plan=${plan.name.toLowerCase()}&currency=${encodeURIComponent(currency)}`)}
                style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8, cursor: loading ? 'wait' : 'pointer', opacity: loading || (plan.price > 0 && !hasAmount) ? 0.6 : 1 }}
              >
                {loading ? 'Updating rate…' : 'Choose'}
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}
