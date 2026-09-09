import React, { useEffect, useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { createCheckout, getExchangeRate, getPaymentGateways } from '../lib/financialApi'

const PLAN_PRICES_USD = { free: 0, starter: 9, pro: 29, business: 99, enterprise: 299 }
const PLAN_NAMES = { free: 'Free', starter: 'Starter', pro: 'Pro', business: 'Business', enterprise: 'Enterprise' }

export default function CheckoutCurrencySafe() {
  const location = useLocation()
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
  const [phone, setPhone] = useState('')
  const [loadingQuote, setLoadingQuote] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => {
    getPaymentGateways().then(data => {
      const live = (data?.gateways || []).filter(g => g.live)
      setGateways(live)
      const compatible = live.find(g => !g.currencies?.length || g.currencies.map(String).map(x => x.toUpperCase()).includes(currency))
      if (compatible) setGateway(compatible.name)
    }).catch(e => setError(e.message))
  }, [currency])

  useEffect(() => {
    let cancelled = false
    async function quote() {
      setError('')
      if (currency === 'USD' || baseAmount === 0) {
        setRate(1); setAmount(String(baseAmount)); return
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
        if (!cancelled) setError(`Unable to quote ${currency}: ${e.message}`)
      } finally { if (!cancelled) setLoadingQuote(false) }
    }
    quote()
    return () => { cancelled = true }
  }, [currency, baseAmount])

  const selectedGateway = gateways.find(g => g.name === gateway)
  const supported = !selectedGateway?.currencies?.length || selectedGateway.currencies.map(String).map(x => x.toUpperCase()).includes(currency)

  async function submit(event) {
    event.preventDefault()
    const numeric = Number(amount)
    if (!Number.isFinite(numeric) || numeric <= 0) { setError('Amount must be greater than zero'); return }
    if (!supported) { setError(`${gateway} does not support ${currency}`); return }
    setWorking(true); setError(''); setResult(null)
    try {
      const data = await createCheckout({
        gateway, amount: numeric, currency,
        reference: `shopnoltd-plan-${plan}-${crypto.randomUUID()}`,
        customer_phone: phone || undefined,
      })
      setResult(data)
      if (data?.redirect_url) window.location.assign(data.redirect_url)
    } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  return <main style={{ maxWidth: 760, margin: '0 auto', padding: 28 }}>
    <h1>Checkout — {PLAN_NAMES[plan]}</h1>
    <p>Prices are based on USD and converted with the current exchange quote. The charge amount and currency are sent together to the selected gateway.</p>
    <form onSubmit={submit} style={{ display: 'grid', gap: 16, border: '1px solid #e2e8f0', borderRadius: 14, padding: 20 }}>
      <label>Base price (USD)<input value={baseAmount} readOnly style={input} /></label>
      <label>Currency<select value={currency} onChange={e => setCurrency(e.target.value)} style={input}><option>USD</option><option>BDT</option><option>EUR</option><option>GBP</option><option>INR</option><option>AUD</option><option>CAD</option><option>SGD</option></select></label>
      <label>Charge amount ({currency})<input value={amount} onChange={e => setAmount(e.target.value)} type="number" min="0.00000001" step="any" required style={input} /></label>
      {currency !== 'USD' && <small>Live quote: 1 USD = {rate} {currency}{loadingQuote ? ' · updating…' : ''}</small>}
      <label>Gateway<select value={gateway} onChange={e => setGateway(e.target.value)} style={input}>{gateways.length === 0 ? <option value="stripe">stripe</option> : gateways.map(g => <option key={g.name} value={g.name}>{g.display_name || g.name}</option>)}</select></label>
      <label>Phone<input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Optional" style={input} /></label>
      {selectedGateway && !supported && <div style={{ color: '#92400e' }}>Selected gateway does not advertise {currency}; choose a compatible gateway.</div>}
      {error && <div style={{ color: '#991b1b' }}>{error}</div>}
      <button disabled={working || loadingQuote || !supported} type="submit">{working ? 'Creating checkout…' : 'Continue to payment'}</button>
      {result && <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>}
    </form>
  </main>
}

const input = { width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5, border: '1px solid #cbd5e1', borderRadius: 8 }
