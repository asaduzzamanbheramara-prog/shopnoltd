import React, { useEffect, useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  convertExchange,
  createCheckout,
  getExchangeRate,
  getPaymentGateways,
  getTransactions,
  getWallet,
  getWalletLedger,
} from '../lib/financialApi'

const PLAN_PRICES = {
  free: 0,
  starter: 9,
  pro: 29,
  business: 99,
  enterprise: 299,
}

const PLAN_NAMES = {
  free: 'Free',
  starter: 'Starter',
  pro: 'Pro',
  business: 'Business',
  enterprise: 'Enterprise',
}

function Card({ title, children }) {
  return (
    <section
      style={{
        background: '#fff',
        border: '1px solid #e2e8f0',
        borderRadius: 14,
        padding: 20,
        boxShadow: '0 2px 8px rgba(15,23,42,.04)',
      }}
    >
      <h2 style={{ marginTop: 0 }}>{title}</h2>
      {children}
    </section>
  )
}

function ErrorBox({ message }) {
  if (!message) return null
  return (
    <div
      style={{
        marginBottom: 16,
        padding: 12,
        borderRadius: 8,
        background: '#fef2f2',
        color: '#991b1b',
        border: '1px solid #fecaca',
      }}
    >
      {message}
    </div>
  )
}

function FinancialNavigation() {
  const links = [
    ['Billing', '/billing'],
    ['Checkout', '/checkout'],
    ['Payments', '/payments'],
    ['Transactions', '/transactions'],
    ['Wallet', '/wallet'],
    ['Wallet Ledger', '/wallet/ledger'],
    ['Exchange', '/exchange'],
    ['Subscriptions', '/subscriptions'],
    ['Invoices', '/invoices'],
    ['Reports', '/reports'],
  ]

  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: 8,
        marginBottom: 24,
      }}
    >
      {links.map(([label, path]) => (
        <Link
          key={path}
          to={path}
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            background: '#e0f2fe',
            color: '#075985',
            textDecoration: 'none',
            fontWeight: 600,
            fontSize: 14,
          }}
        >
          {label}
        </Link>
      ))}
    </div>
  )
}

function WalletView() {
  const [currency, setCurrency] = useState('BDT')
  const [wallet, setWallet] = useState(null)
  const [ledger, setLedger] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError(null)

    try {
      const [w, l] = await Promise.all([
        getWallet(currency),
        getWalletLedger(currency),
      ])
      setWallet(w)
      setLedger(Array.isArray(l) ? l : [])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [currency])

  return (
    <>
      <Card title="Wallet">
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            style={{ padding: 10, borderRadius: 8, border: '1px solid #cbd5e1' }}
          >
            <option>BDT</option>
            <option>USD</option>
            <option>EUR</option>
            <option>GBP</option>
          </select>

          <button
            onClick={load}
            style={{
              padding: '10px 16px',
              border: 0,
              borderRadius: 8,
              background: '#0ea5e9',
              color: '#fff',
              cursor: 'pointer',
            }}
          >
            Refresh
          </button>
        </div>

        <ErrorBox message={error} />

        {loading ? (
          <p>Loading wallet…</p>
        ) : (
          <div
            style={{
              marginTop: 18,
              padding: 20,
              borderRadius: 12,
              background: '#f8fafc',
            }}
          >
            <div style={{ color: '#64748b' }}>{wallet?.currency || currency}</div>
            <div style={{ fontSize: 36, fontWeight: 800 }}>
              {wallet?.balance ?? '0.00'}
            </div>
          </div>
        )}
      </Card>

      <Card title="Wallet Ledger">
        {loading ? (
          <p>Loading ledger…</p>
        ) : ledger.length === 0 ? (
          <p style={{ color: '#64748b' }}>No ledger entries yet.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: 8 }}>Date</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Type</th>
                  <th style={{ textAlign: 'right', padding: 8 }}>Amount</th>
                  <th style={{ textAlign: 'right', padding: 8 }}>Balance</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Reason</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((entry) => (
                  <tr key={entry.id}>
                    <td style={{ padding: 8 }}>{entry.created_at || '—'}</td>
                    <td style={{ padding: 8 }}>{entry.entry_type || '—'}</td>
                    <td style={{ padding: 8, textAlign: 'right' }}>
                      {entry.amount ?? '—'}
                    </td>
                    <td style={{ padding: 8, textAlign: 'right' }}>
                      {entry.balance_after ?? '—'}
                    </td>
                    <td style={{ padding: 8 }}>{entry.reason || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </>
  )
}

function TransactionsView() {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getTransactions()
      .then((data) => setItems(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Card title="Transactions">
      <ErrorBox message={error} />
      {loading ? (
        <p>Loading transactions…</p>
      ) : items.length === 0 ? (
        <p style={{ color: '#64748b' }}>No transactions yet.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: 8 }}>ID</th>
                <th style={{ textAlign: 'left', padding: 8 }}>Gateway</th>
                <th style={{ textAlign: 'right', padding: 8 }}>Amount</th>
                <th style={{ textAlign: 'left', padding: 8 }}>Currency</th>
                <th style={{ textAlign: 'left', padding: 8 }}>Status</th>
                <th style={{ textAlign: 'left', padding: 8 }}>Created</th>
              </tr>
            </thead>
            <tbody>
              {items.map((tx) => (
                <tr key={tx.id}>
                  <td style={{ padding: 8 }}>{tx.id}</td>
                  <td style={{ padding: 8 }}>{tx.gateway}</td>
                  <td style={{ padding: 8, textAlign: 'right' }}>{tx.amount}</td>
                  <td style={{ padding: 8 }}>{tx.currency}</td>
                  <td style={{ padding: 8 }}>
                    {tx.status}
                    {tx.is_demo ? ' (demo)' : ''}
                  </td>
                  <td style={{ padding: 8 }}>{tx.created_at || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

function GatewayView() {
  const [gateways, setGateways] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    getPaymentGateways()
      .then((data) => setGateways(data?.gateways || []))
      .catch((err) => setError(err.message))
  }, [])

  return (
    <Card title="Payment Gateways">
      <ErrorBox message={error} />
      {gateways.length === 0 ? (
        <p style={{ color: '#64748b' }}>No gateway data returned.</p>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12,
          }}
        >
          {gateways.map((gateway) => (
            <div
              key={gateway.name}
              style={{
                padding: 16,
                border: '1px solid #e2e8f0',
                borderRadius: 10,
              }}
            >
              <strong>{gateway.name}</strong>
              <p style={{ marginBottom: 6 }}>
                Status:{' '}
                <strong>{gateway.live ? 'LIVE' : 'NOT LIVE'}</strong>
              </p>
              <p style={{ margin: 0, color: '#64748b' }}>
                Credentials:{' '}
                {gateway.credentials_configured ? 'configured' : 'not configured'}
              </p>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}

function CheckoutView() {
  const location = useLocation()
  const params = useMemo(
    () => new URLSearchParams(location.search),
    [location.search]
  )

  const requestedPlan = (params.get('plan') || 'starter').toLowerCase()
  const plan = PLAN_NAMES[requestedPlan] ? requestedPlan : 'starter'

  const [amount, setAmount] = useState(String(PLAN_PRICES[plan]))
  const [currency, setCurrency] = useState('USD')
  const [gateway, setGateway] = useState('stripe')
  const [phone, setPhone] = useState('')
  const [gateways, setGateways] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [working, setWorking] = useState(false)

  useEffect(() => {
    getPaymentGateways()
      .then((data) => {
        const live = (data?.gateways || []).filter((g) => g.live)
        setGateways(live)
        if (live.length && !live.some((g) => g.name === gateway)) {
          setGateway(live[0].name)
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  async function submit(e) {
    e.preventDefault()
    setWorking(true)
    setError(null)
    setResult(null)

    try {
      const data = await createCheckout({
        gateway,
        amount,
        currency,
        reference: `shopnoltd-plan-${plan}-${Date.now()}`,
        customer_phone: phone || undefined,
      })

      setResult(data)

      if (data?.redirect_url) {
        window.location.assign(data.redirect_url)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setWorking(false)
    }
  }

  return (
    <Card title={`Checkout — ${PLAN_NAMES[plan]}`}>
      <form onSubmit={submit}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: 14,
          }}
        >
          <label>
            Amount
            <input
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              type="number"
              min="0"
              step="0.01"
              required
              style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }}
            />
          </label>

          <label>
            Currency
            <select
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              style={{ width: '100%', padding: 10, marginTop: 5 }}
            >
              <option>USD</option>
              <option>BDT</option>
              <option>EUR</option>
              <option>GBP</option>
            </select>
          </label>

          <label>
            Gateway
            <select
              value={gateway}
              onChange={(e) => setGateway(e.target.value)}
              style={{ width: '100%', padding: 10, marginTop: 5 }}
            >
              {gateways.length === 0 && <option value="stripe">stripe</option>}
              {gateways.map((g) => (
                <option key={g.name} value={g.name}>
                  {g.name}
                </option>
              ))}
            </select>
          </label>

          <label>
            Phone
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Optional"
              style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }}
            />
          </label>
        </div>

        <ErrorBox message={error} />

        <button
          disabled={working}
          type="submit"
          style={{
            marginTop: 20,
            padding: '12px 20px',
            border: 0,
            borderRadius: 8,
            background: '#0ea5e9',
            color: '#fff',
            fontWeight: 700,
            cursor: working ? 'wait' : 'pointer',
          }}
        >
          {working ? 'Creating checkout…' : 'Continue to payment'}
        </button>
      </form>

      {result && (
        <div
          style={{
            marginTop: 20,
            padding: 16,
            borderRadius: 10,
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
          }}
        >
          <strong>Checkout created</strong>
          <p>Status: {result.status}</p>
          <p>Transaction: {result.transaction_id}</p>
          {result.gateway_reference && (
            <p>Gateway reference: {result.gateway_reference}</p>
          )}
          {result.note && <p>{result.note}</p>}
        </div>
      )}
    </Card>
  )
}

function ExchangeView() {
  const [from, setFrom] = useState('USD')
  const [to, setTo] = useState('BDT')
  const [amount, setAmount] = useState('100')
  const [rate, setRate] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [working, setWorking] = useState(false)

  async function loadRate() {
    setError(null)
    try {
      setRate(await getExchangeRate(from, to))
    } catch (err) {
      setError(err.message)
    }
  }

  async function convert() {
    setWorking(true)
    setError(null)
    setResult(null)

    try {
      const data = await convertExchange({
        from_currency: from,
        to_currency: to,
        amount,
      })
      setResult(data)
      setRate({
        base: data.from_currency,
        quote: data.to_currency,
        rate: data.rate,
        source: data.source,
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setWorking(false)
    }
  }

  return (
    <Card title="Exchange">
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 12,
        }}
      >
        <label>
          From
          <select
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            style={{ width: '100%', padding: 10, marginTop: 5 }}
          >
            <option>USD</option>
            <option>BDT</option>
            <option>EUR</option>
            <option>GBP</option>
            <option>INR</option>
          </select>
        </label>

        <label>
          To
          <select
            value={to}
            onChange={(e) => setTo(e.target.value)}
            style={{ width: '100%', padding: 10, marginTop: 5 }}
          >
            <option>BDT</option>
            <option>USD</option>
            <option>EUR</option>
            <option>GBP</option>
            <option>INR</option>
          </select>
        </label>

        <label>
          Amount
          <input
            type="number"
            min="0.000001"
            step="any"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }}
          />
        </label>
      </div>

      <ErrorBox message={error} />

      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 16 }}>
        <button
          onClick={loadRate}
          style={{
            padding: '10px 16px',
            border: 0,
            borderRadius: 8,
            background: '#334155',
            color: '#fff',
            cursor: 'pointer',
          }}
        >
          Get live rate
        </button>

        <button
          onClick={convert}
          disabled={working}
          style={{
            padding: '10px 16px',
            border: 0,
            borderRadius: 8,
            background: '#0ea5e9',
            color: '#fff',
            cursor: working ? 'wait' : 'pointer',
          }}
        >
          {working ? 'Converting…' : 'Convert'}
        </button>
      </div>

      {rate && (
        <div style={{ marginTop: 20, padding: 16, background: '#f8fafc', borderRadius: 10 }}>
          <strong>
            1 {rate.base || from} = {rate.rate} {rate.quote || to}
          </strong>
          <p style={{ marginBottom: 0 }}>
            Source: {rate.source || 'exchange service'}
          </p>
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: 14,
            padding: 16,
            borderRadius: 10,
            background: '#f0fdf4',
            border: '1px solid #bbf7d0',
          }}
        >
          <strong>Conversion result</strong>
          <p>
            {result.from_amount} {result.from_currency} → {result.to_amount}{' '}
            {result.to_currency}
          </p>
          <p>Rate: {result.rate}</p>
          <p>Fee: {result.fee}</p>
          <p>Source: {result.source}</p>
        </div>
      )}
    </Card>
  )
}

function UnsupportedView({ title }) {
  return (
    <Card title={title}>
      <div
        style={{
          padding: 16,
          background: '#fff7ed',
          border: '1px solid #fed7aa',
          borderRadius: 10,
          color: '#9a3412',
        }}
      >
        <strong>This UI route is ready, but the backend contract is not yet
        exposed.</strong>
        <p>
          No fake financial records are shown. The next backend patch must
          expose the real {title.toLowerCase()} data before this screen can
          display production information.
        </p>
      </div>
    </Card>
  )
}

export default function FinancialCenter({ view = 'billing' }) {
  const titles = {
    billing: 'Billing',
    checkout: 'Checkout',
    payments: 'Payments',
    transactions: 'Transactions',
    wallet: 'Wallet',
    ledger: 'Wallet Ledger',
    exchange: 'Exchange',
    subscriptions: 'Subscriptions',
    invoices: 'Invoices',
    reports: 'Reports',
  }

  const title = titles[view] || 'Billing'

  return (
    <main
      style={{
        maxWidth: 1180,
        margin: '0 auto',
        padding: '32px 16px 80px',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <h1>{title}</h1>
      <p style={{ color: '#64748b' }}>
        Shopnoltd financial services use authenticated platform APIs. No
        browser-side internal billing secrets are used.
      </p>

      <FinancialNavigation />

      <div style={{ display: 'grid', gap: 18 }}>
        {view === 'wallet' || view === 'ledger' ? <WalletView /> : null}
        {view === 'transactions' || view === 'payments' ? <TransactionsView /> : null}
        {view === 'billing' ? <GatewayView /> : null}
        {view === 'checkout' ? <CheckoutView /> : null}
        {view === 'exchange' ? <ExchangeView /> : null}
        {view === 'subscriptions' ? (
          <UnsupportedView title="Subscriptions" />
        ) : null}
        {view === 'invoices' ? <UnsupportedView title="Invoices" /> : null}
        {view === 'reports' ? <UnsupportedView title="Reports" /> : null}
      </div>
    </main>
  )
}
