import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { getExchangeRate } from '../lib/financialApi'
import { formatFinancialAmount, getPreferredFinancialCurrency, useFinancialCurrency } from '../lib/financialCurrency'

const CURRENCIES = ['USD', 'EUR', 'GBP', 'BDT', 'INR', 'PKR', 'MYR', 'NGN', 'ZAR', 'USDT', 'BTC', 'ETH', 'BNB', 'SOL', 'TRX', 'XRP', 'ADA', 'DOGE', 'USDC']
const RATE_REFRESH_MS = 5 * 60 * 1000
const MAX_RATE_AGE_MS = 24 * 60 * 60 * 1000

function Card({ children }) {
  return <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 20, boxShadow: '0 2px 8px rgba(15,23,42,.04)' }}>{children}</section>
}

export default function ExchangeCalculator() {
  const [from, setFrom] = useFinancialCurrency()
  const [to, setTo] = useState(() => getPreferredFinancialCurrency() === 'USD' ? 'BDT' : 'USD')
  const [amount, setAmount] = useState('100')
  const [rate, setRate] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const refreshRate = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const quote = await getExchangeRate(from, to)
      const value = Number(quote?.rate)
      if (!Number.isFinite(value) || value <= 0) throw new Error('The exchange service returned an invalid rate.')
      setRate({ ...quote, rate: value })
    } catch (err) {
      setRate(null)
      setError(err?.message || 'Exchange rate is currently unavailable.')
    } finally {
      setLoading(false)
    }
  }, [from, to])

  useEffect(() => {
    void refreshRate()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refreshRate()
    }, RATE_REFRESH_MS)
    const onVisible = () => {
      if (document.visibilityState === 'visible') void refreshRate()
    }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [refreshRate])

  const numericAmount = Number(amount)
  const converted = useMemo(() => {
    if (!rate || !Number.isFinite(numericAmount) || numericAmount < 0) return null
    return numericAmount * rate.rate
  }, [rate, numericAmount])

  const timestamp = rate?.timestamp || rate?.fetched_at || ''
  const timestampMs = timestamp ? Date.parse(timestamp) : NaN
  const isIdentity = rate?.source === 'identity' || from === to
  const stale = !isIdentity && (!Number.isFinite(timestampMs) || Date.now() - timestampMs > MAX_RATE_AGE_MS)

  return (
    <Card>
      <h2 style={{ marginTop: 0 }}>Exchange Rate Calculator</h2>
      <p style={{ color: '#64748b', marginTop: -6 }}>Check the latest available rate and preview a conversion. This calculator does not debit a wallet, create a transaction or execute a currency exchange.</p>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(170px,1fr))', gap: 12 }}>
        <label style={{ display: 'grid', gap: 5 }}>From currency
          <select value={from} onChange={e => setFrom(e.target.value)} style={{ width: '100%', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }}>
            {CURRENCIES.map(code => <option key={code}>{code}</option>)}
          </select>
        </label>
        <div style={{ display: 'flex', alignItems: 'end' }}>
          <button type="button" onClick={() => { setFrom(to); setTo(from) }} style={{ width: '100%', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8, background: '#f8fafc', cursor: 'pointer' }}>⇄ Swap currencies</button>
        </div>
        <label style={{ display: 'grid', gap: 5 }}>To currency
          <select value={to} onChange={e => setTo(e.target.value)} style={{ width: '100%', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }}>
            {CURRENCIES.map(code => <option key={code}>{code}</option>)}
          </select>
        </label>
        <label style={{ display: 'grid', gap: 5 }}>Amount
          <input type="number" min="0" step="any" value={amount} onChange={e => setAmount(e.target.value)} style={{ width: '100%', boxSizing: 'border-box', padding: 10, border: '1px solid #cbd5e1', borderRadius: 8 }} />
        </label>
      </div>

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 16 }}>
        <button type="button" onClick={refreshRate} disabled={loading} style={{ padding: '10px 16px', border: 0, borderRadius: 8, background: '#334155', color: '#fff', cursor: loading ? 'wait' : 'pointer' }}>{loading ? 'Updating rate…' : 'Refresh rate'}</button>
      </div>

      {error && <div role="alert" style={{ marginTop: 16, padding: 12, borderRadius: 8, color: '#991b1b', background: '#fef2f2', border: '1px solid #fecaca' }}>{error} No fallback or guessed rate is being displayed.</div>}

      {rate && <div style={{ marginTop: 18, padding: 18, borderRadius: 12, background: '#f8fafc', border: '1px solid #e2e8f0' }}>
        <div style={{ color: '#64748b', fontSize: 13 }}>Available reference rate</div>
        <div style={{ fontSize: 20, fontWeight: 700, marginTop: 4 }}>1 {from} = {rate.rate.toLocaleString(undefined, { maximumFractionDigits: 8 })} {to}</div>
        <div style={{ marginTop: 12, fontSize: 13, color: '#475569' }}>Source: {rate.source || 'Exchange service'}</div>
        <div style={{ fontSize: 13, color: '#475569' }}>Last updated: {Number.isFinite(timestampMs) ? new Date(timestampMs).toLocaleString() : 'Timestamp not supplied'}</div>
        {stale && <div role="status" style={{ marginTop: 10, color: '#9a3412', background: '#fff7ed', padding: 10, borderRadius: 8 }}>Warning: this rate is older than 24 hours or has no valid timestamp. Refresh before relying on it.</div>}
      </div>}

      {rate && converted !== null && <div aria-live="polite" style={{ marginTop: 14, padding: 18, borderRadius: 12, background: '#eff6ff', border: '1px solid #bfdbfe' }}>
        <div style={{ color: '#1e40af', fontSize: 13 }}>Estimated conversion · calculator only</div>
        <div style={{ fontSize: 28, fontWeight: 800, color: '#0f172a', overflowWrap: 'anywhere' }}>{formatFinancialAmount(numericAmount, from)} = {formatFinancialAmount(converted, to)}</div>
        <p style={{ marginBottom: 0, color: '#475569', fontSize: 13 }}>This preview uses the reference rate shown above and excludes provider, network and wallet fees. No money has been moved.</p>
      </div>}
    </Card>
  )
}
