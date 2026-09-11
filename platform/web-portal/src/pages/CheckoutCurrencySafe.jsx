import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { createCheckout, createDirectPaymentIntent, getDirectPaymentAccounts, getExchangeRate, getPaymentGateways, submitDirectPayment } from '../lib/financialApi'

const PLAN_PRICES_USD = { free: 0, starter: 9, pro: 29, business: 99, enterprise: 299 }
const PLAN_NAMES = { free: 'Free', starter: 'Starter', pro: 'Pro', business: 'Business', enterprise: 'Enterprise' }
const FALLBACK_CURRENCIES = ['USD', 'BDT', 'EUR', 'GBP', 'INR', 'AUD', 'CAD', 'SGD']

export default function CheckoutCurrencySafe() {
  const location = useLocation(); const navigate = useNavigate()
  const plan = useMemo(() => { const value = (new URLSearchParams(location.search).get('plan') || 'starter').toLowerCase(); return PLAN_NAMES[value] ? value : 'starter' }, [location.search])
  const baseAmount = PLAN_PRICES_USD[plan]
  const [currency, setCurrency] = useState('USD'); const [amount, setAmount] = useState(String(baseAmount)); const [rate, setRate] = useState(1)
  const [gateway, setGateway] = useState('stripe'); const [gateways, setGateways] = useState([]); const [currencies, setCurrencies] = useState(FALLBACK_CURRENCIES)
  const [mode, setMode] = useState('online'); const [directProvider, setDirectProvider] = useState('bkash'); const [directAccounts, setDirectAccounts] = useState([]); const [directAccount, setDirectAccount] = useState(null)
  const [intent, setIntent] = useState(null); const [txid, setTxid] = useState(''); const [senderNumber, setSenderNumber] = useState('')
  const [phone, setPhone] = useState(''); const [loadingQuote, setLoadingQuote] = useState(false); const [working, setWorking] = useState(false); const [error, setError] = useState(''); const [result, setResult] = useState(null)

  useEffect(() => {
    getPaymentGateways().then(data => {
      const live = (data?.gateways || []).filter(g => g.live && g.available !== false)
      setGateways(live)
      const available = [...new Set(live.flatMap(g => (g.currencies || []).map(x => String(x).toUpperCase())))]
      if (available.length) { setCurrencies(available.sort()); if (!available.includes(currency)) setCurrency(available.includes('USD') ? 'USD' : available[0]) }
    }).catch(e => setError(e.message))
  }, [])

  useEffect(() => {
    const compatible = gateways.filter(g => !g.currencies?.length || g.currencies.map(String).map(x => x.toUpperCase()).includes(currency))
    if (compatible.length && !compatible.some(g => g.name === gateway)) setGateway(compatible[0].name)
  }, [currency, gateways, gateway])

  useEffect(() => {
    let cancelled = false
    async function quote() {
      setError('')
      if (baseAmount === 0 || currency === 'USD') { setRate(1); setAmount(String(baseAmount)); return }
      setLoadingQuote(true)
      try {
        const data = await getExchangeRate('USD', currency); const nextRate = Number(data?.rate)
        if (!Number.isFinite(nextRate) || nextRate <= 0) throw new Error('Invalid live exchange rate')
        if (!cancelled) { setRate(nextRate); setAmount((baseAmount * nextRate).toFixed(2)) }
      } catch (e) { if (!cancelled) { setRate(null); setAmount(''); setError(`Unable to quote ${currency}: ${e.message}`) } }
      finally { if (!cancelled) setLoadingQuote(false) }
    }
    quote(); return () => { cancelled = true }
  }, [currency, baseAmount])

  useEffect(() => {
    if (mode !== 'direct') return
    getDirectPaymentAccounts(directProvider).then(data => {
      const accounts = data?.accounts || []; setDirectAccounts(accounts); setDirectAccount(accounts[0] || null); setIntent(null); setTxid(''); setSenderNumber('')
    }).catch(e => { setDirectAccounts([]); setDirectAccount(null); setError(e.message) })
  }, [mode, directProvider])

  const selectedGateway = gateways.find(g => g.name === gateway)
  const supported = !!selectedGateway && (!selectedGateway.currencies?.length || selectedGateway.currencies.map(String).map(x => x.toUpperCase()).includes(currency))
  const compatibleGateways = gateways.filter(g => !g.currencies?.length || g.currencies.map(String).map(x => x.toUpperCase()).includes(currency))

  async function submitOnline(event) {
    event.preventDefault(); const numeric = Number(amount)
    if (!Number.isFinite(numeric) || numeric <= 0) { setError('Amount must be greater than zero'); return }
    if (!selectedGateway || !supported) { setError('Choose a live gateway that supports the selected currency'); return }
    setWorking(true); setError(''); setResult(null)
    try {
      const data = await createCheckout({ gateway, amount: numeric, currency, reference: `shopnoltd-plan-${plan}-${crypto.randomUUID()}`, customer_phone: phone || undefined })
      setResult(data); if (data?.redirect_url) window.location.assign(data.redirect_url); else if (data?.checkout_url) window.location.assign(data.checkout_url)
    } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  async function startDirect(event) {
    event.preventDefault(); const numeric = Number(amount)
    if (!Number.isFinite(numeric) || numeric <= 0) { setError('Amount must be greater than zero'); return }
    if (currency !== 'BDT') { setError('Direct-number payments currently require BDT'); return }
    if (!directAccount) { setError(`No active ${directProvider} receiving account is configured`); return }
    setWorking(true); setError(''); setResult(null)
    try {
      const data = await createDirectPaymentIntent({ provider: directProvider, amount: numeric, currency, account_id: directAccount.id, order_id: `shopnoltd-plan-${plan}` })
      setIntent(data); setResult(data)
    } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  async function verifyDirect(event) {
    event.preventDefault()
    if (!intent || !txid.trim()) { setError('Enter the payment TxID after sending the exact amount'); return }
    setWorking(true); setError('')
    try {
      const data = await submitDirectPayment({ intent_id: intent.id, txid: txid.trim(), sender_number: senderNumber.trim() || undefined, amount: Number(amount), reference: intent.expected_reference })
      setResult(data)
    } catch (e) { setError(e.message) } finally { setWorking(false) }
  }

  return <main style={{ maxWidth: 760, margin: '0 auto', padding: 28 }}>
    <h1>Checkout — {PLAN_NAMES[plan]}</h1>
    <p>Online gateways use their provider checkout. Direct-number payments show a configured bKash, Nagad or Rocket receiving account and require a TxID submission; a submitted TxID is not treated as proof until independently verified.</p>
    <form onSubmit={mode === 'online' ? submitOnline : (intent ? verifyDirect : startDirect)} style={{ display: 'grid', gap: 16, border: '1px solid #e2e8f0', borderRadius: 14, padding: 20 }}>
      <label>Payment mode<select value={mode} onChange={e => { setMode(e.target.value); setResult(null); setError('') }} style={input}><option value="online">Online gateway</option><option value="direct">Pay to bKash/Nagad/Rocket number</option></select></label>
      <label>Base price (USD)<input value={baseAmount.toFixed(2)} readOnly style={input} /></label>
      <label>Currency<select value={currency} onChange={e => setCurrency(e.target.value)} style={input}>{currencies.map(c => <option key={c} value={c}>{c}</option>)}</select></label>
      <label>Calculated charge ({currency})<input value={amount} readOnly type="number" style={input} /></label>
      {currency !== 'USD' && <small>{rate ? `Live quote: 1 USD = ${rate} ${currency}` : loadingQuote ? 'Updating live quote…' : 'Live quote unavailable'}</small>}
      {mode === 'online' ? <>
        <label>Online payment gateway<select value={gateway} onChange={e => setGateway(e.target.value)} style={input}>{compatibleGateways.map(g => <option key={g.name} value={g.name}>{g.display_name || g.name}</option>)}</select></label>
        {selectedGateway?.payment_methods?.length > 0 && <small>Payment methods: {selectedGateway.payment_methods.join(', ')}</small>}
        <label>Phone<input value={phone} onChange={e => setPhone(e.target.value)} placeholder="Optional" style={input} /></label>
        {!compatibleGateways.length && <div style={{ color: '#991b1b' }}>No live online gateway currently supports {currency}.</div>}
        <button disabled={working || loadingQuote || !supported || !amount} type="submit">{working ? 'Creating secure payment…' : 'Continue to secure payment'}</button>
      </> : <>
        <label>Provider<select value={directProvider} disabled={!!intent} onChange={e => setDirectProvider(e.target.value)} style={input}><option value="bkash">bKash</option><option value="nagad">Nagad</option><option value="rocket">Rocket</option></select></label>
        {directAccount && !intent && <div style={{ border: '1px solid #cbd5e1', borderRadius: 8, padding: 12 }}><strong>Send exactly {amount} BDT</strong><br />Receiver: {directAccount.account_number}<br />Account type: {directAccount.account_type}<br />{directAccount.instructions || 'Use the exact reference shown after creating the payment intent.'}</div>}
        {!intent && <button disabled={working || loadingQuote || currency !== 'BDT' || !directAccount || !amount} type="submit">{working ? 'Preparing payment instructions…' : 'Show payment instructions'}</button>}
        {intent && <>
          <div style={{ border: '1px solid #cbd5e1', borderRadius: 8, padding: 12 }}><strong>Payment instructions</strong><br />Send exactly {intent.amount} {intent.currency} to {intent.account?.account_number}.<br />Reference: <strong>{intent.expected_reference}</strong><br />Status: {intent.status}</div>
          <label>TxID<input value={txid} onChange={e => setTxid(e.target.value)} required placeholder="Transaction ID from the payment app" style={input} /></label>
          <label>Sender number<input value={senderNumber} onChange={e => setSenderNumber(e.target.value)} placeholder="Optional, if available" style={input} /></label>
          <button disabled={working || !txid.trim()} type="submit">{working ? 'Submitting…' : 'Submit TxID for verification'}</button>
        </>}
      </>}
      {error && <div style={{ color: '#991b1b' }}>{error}</div>}
      <button type="button" onClick={() => navigate('/payments')}>Open payment center</button>
      {result && <pre style={{ whiteSpace: 'pre-wrap', overflowX: 'auto' }}>{JSON.stringify(result, null, 2)}</pre>}
    </form>
  </main>
}

const input = { width: '100%', boxSizing: 'border-box', padding: 10, marginTop: 5, border: '1px solid #cbd5e1', borderRadius: 8 }
