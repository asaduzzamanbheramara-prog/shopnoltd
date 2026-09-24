import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createCheckout, getExchangeRate, getPaymentGateways } from '../lib/financialApi'

const PLAN_PRICES_USD = { free: 0, starter: 9, pro: 29, business: 99, enterprise: 299 }
const PLAN_NAMES = { free: 'Free', starter: 'Starter', pro: 'Pro', business: 'Business', enterprise: 'Enterprise' }
const FALLBACK_CURRENCIES = ['USD', 'BDT', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'SGD']

export default function CheckoutCurrencySafe() {
  const location = useLocation()
  const navigate = useNavigate()
  const plan = useMemo(() => {
    const value = (new URLSearchParams(location.search).get('plan') || 'starter').toLowerCase()
    return PLAN_NAMES[value] ? value : 'starter'
  }, [location.search])

  const baseAmount = PLAN_PRICES_USD[plan]
  const [currency, setCurrency] = useState('USD')
  const [amount, setAmount] = useState(String(baseAmount))
  const [rate, setRate] = useState(1)
  const [gateway, setGateway] = useState('stripe')
  const [gateways, setGateways] = useState([])
  const [currencies, setCurrencies] = useState(FALLBACK_CURRENCIES)
  const [phone, setPhone] = useState('')
  const [loadingQuote, setLoadingQuote] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    getPaymentGateways().then(data => {
      const live = (data?.gateways || []).filter(g => g.live && g.available !== false)
      setGateways(live)
      const available = [...new Set(live.flatMap(g => (g.currencies || []).map(x => String(x).toUpperCase())))]
      if (available.length) {
        setCurrencies(available.sort())
        if (!available.includes(currency)) setCurrency(available.includes('USD') ? 'USD' : available[0])
      }
    }).catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    const compatible = gateways.filter(g => !g.currencies?.length || g.currencies.map(String).map(x => x.toUpperCase()).includes(currency))
    if (!compatible.length) return
    // For BDT, prefer the hosted Moneybag checkout because it presents bKash,
    // Nagad, Rocket and cards in one customer-facing payment page.
    const preferred = currency === 'BDT'
      ? compatible.find(g => g.name === 'moneybag') || compatible[0]
      : compatible.find(g => g.name === gateway) || compatible[0]
    if (preferred && preferred.name !== gateway) setGateway(preferred.name)
  }, [currency, gateways, gateway])

  useEffect(() => {
    let cancelled = false
    async function quote() {
      setError('')
      if (baseAmount === 0 || currency === 'USD') {
        setRate(1)
        setAmount(String(baseAmount))
        return
      }
      setLoadingQuote(true)
      try {
        const data = await getExchangeRate('USD', currency)
        const nextRate = Number(data?.rate)
        if (!Number.isFinite(nextRate) || nextRate <= 0) throw new Error('Invalid live exchange rate')
        if (!cancelled) {
          setRate(nextRate)
          setAmount((baseAmount * nextRate).toFixed(2))
        }
      } catch (e) {
        if (!cancelled) {
          setRate(null)
          setAmount('')
          setError(`Unable to quote ${currency}: ${e.message}`)
        }
      } finally {
        if (!cancelled) setLoadingQuote(false)
      }
    }
    quote()
    return () => { cancelled = true }
  }, [currency, baseAmount])

  const selectedGateway = gateways.find(g => g.name === gateway)
  const compatibleGateways = gateways.filter(
    g => !g.currencies?.length || g.currencies.map(String).map(x => x.toUpperCase()).includes(currency)
  )
  const supported = !!selectedGateway && (
    !selectedGateway.currencies?.length ||
    selectedGateway.currencies.map(String).map(x => x.toUpperCase()).includes(currency)
  )

  async function submitOnline(event) {
    event.preventDefault()
    const numeric = Number(amount)
    if (!Number.isFinite(numeric) || numeric <= 0) {
      setError('Amount must be greater than zero')
      return
    }
    if (!selectedGateway || !supported) {
      setError('Choose a live gateway that supports the selected currency')
      return
    }
    if (selectedGateway.name === 'moneybag' && currency === 'BDT' && (!phone || !/^01[3-9]\\d{8}$/.test(phone.replace(/\\s+/g, '')))) {
      setError('Enter a valid Bangladesh mobile number for the hosted checkout')
      return
    }

    setWorking(true)
    setError('')
    setResult(null)
    try {
      const data = await createCheckout({
        gateway,
        amount: numeric,
        currency,
        reference: `shopnoltd-plan-${plan}-${crypto.randomUUID()}`,
        customer_phone: phone || undefined,
      })
      setResult(data)
      const redirect = data?.redirect_url || data?.checkout_url
      if (redirect) window.location.assign(redirect)
    } catch (e) {
      setError(e.message)
    } finally {
      setWorking(false)
    }
  }

  return (
    <main style={{ maxWidth: 760, margin: '0 auto', padding: 28 }}>
      <h1>Checkout — {PLAN_NAMES[plan]}</h1>
      <p>
        Secure hosted checkout. For BDT, the Moneybag checkout can present bKash,
        Nagad, Rocket and supported cards without asking the customer for a
        Shopnoltd merchant number.
      </p>

      <form onSubmit={submitOnline} style={{ display: 'grid', gap: 16, border: '1px solid #e2e8f0', borderRadius: 14, padding: 20 }}>
        <label>
          Base price (USD)
          <input value={baseAmount.toFixed(2)} readOnly style={input} />
        </label>

        <label>
          Currency
          <select value={currency} onChange={e => setCurrency(e.target.value)} style={input}>
            {currencies.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>

        <label>
          Calculated charge ({currency})
          <input value={amount} readOnly type="number" style={input} />
        </label>

        {currency !== 'USD' && (
          <small>
            {rate ? `Live quote: 1 USD = ${rate} ${currency}` : loadingQuote ? 'Updating live quote…' : 'Live quote unavailable'}
          </small>
        )}

        <label>
          Secure payment gateway
          <select value={gateway} onChange={e => setGateway(e.target.value)} style={input}>
            {compatibleGateways.map(g => (
              <option key={g.name} value={g.name}>
                {g.display_name || g.name}
              </option>
            ))}
          </select>
        </label>

        {selectedGateway?.payment_methods?.length > 0 && (
          <div style={{ padding: 12, borderRadius: 8, background: '#f8fafc' }}>
            <strong>Available at the hosted checkout:</strong>{' '}
            {selectedGateway.payment_methods.join(', ')}
          </div>
        )}

        {currency === 'BDT' && selectedGateway?.name === 'moneybag' && (
          <label>
            Mobile number
            <input
              value={phone}
              onChange={e => setPhone(e.target.value)}
              placeholder="01XXXXXXXXX"
              inputMode="tel"
              required
              style={input}
            />
          </label>
        )}

        {!compatibleGateways.length && (
          <div style={{ color: '#991b1b' }}>No live online gateway currently supports {currency}.</div>
        )}

        <button disabled={working || loadingQuote || !supported || !amount} type="submit">
          {working ? 'Creating secure payment…' : 'Continue to secure payment'}
        </button>

        {error && <div style={{ color: '#991b1b' }}>{error}</div>}
        {result && <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>}

        <button type="button" onClick={() => navigate('/payments')}>Open payment center</button>
      </form>
    </main>
  )
}

const input = {
  width: '100%',
  boxSizing: 'border-box',
  padding: 10,
  marginTop: 5,
  border: '1px solid #cbd5e1',
  borderRadius: 8,
}
