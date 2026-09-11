import React, { useEffect, useMemo, useState } from 'react'
import { createDirectPaymentIntent, getDirectPaymentAccounts, submitDirectPayment } from '../lib/financialApi'

function Card({ title, children }) {
  return <section style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 14, padding: 20, boxShadow: '0 2px 8px rgba(15,23,42,.04)' }}>
    <h2 style={{ marginTop: 0 }}>{title}</h2>{children}
  </section>
}

export default function DirectPayment() {
  const [accounts, setAccounts] = useState([])
  const [provider, setProvider] = useState('bkash')
  const [amount, setAmount] = useState('')
  const [orderId, setOrderId] = useState('')
  const [intent, setIntent] = useState(null)
  const [senderNumber, setSenderNumber] = useState('')
  const [transactionId, setTransactionId] = useState('')
  const [submittedAmount, setSubmittedAmount] = useState('')
  const [error, setError] = useState(null)
  const [message, setMessage] = useState(null)
  const [working, setWorking] = useState(false)

  useEffect(() => {
    getDirectPaymentAccounts()
      .then((data) => setAccounts(Array.isArray(data?.accounts) ? data.accounts : []))
      .catch((err) => setError(err.message))
  }, [])

  const providers = useMemo(() => [...new Set(accounts.map((a) => a.provider))], [accounts])
  const providerAccounts = accounts.filter((a) => a.provider === provider && a.currency === 'BDT')
  const selectedAccount = providerAccounts[0]

  useEffect(() => {
    if (!providers.includes(provider) && providers.length) setProvider(providers[0])
  }, [providers, provider])

  async function createIntent(e) {
    e.preventDefault()
    setWorking(true); setError(null); setMessage(null)
    try {
      const data = await createDirectPaymentIntent({
        provider,
        amount,
        currency: 'BDT',
        order_id: orderId || undefined,
        account_id: selectedAccount?.id,
      })
      setIntent(data)
      setSubmittedAmount(String(data.amount))
    } catch (err) { setError(err.message) } finally { setWorking(false) }
  }

  async function submitPayment(e) {
    e.preventDefault()
    if (!intent) return
    setWorking(true); setError(null); setMessage(null)
    try {
      const data = await submitDirectPayment(intent.id, {
        sender_number: senderNumber || undefined,
        transaction_id: transactionId,
        submitted_amount: submittedAmount,
        submitted_currency: 'BDT',
      })
      setMessage(data.note || `Payment status: ${data.status}`)
      setIntent((old) => ({ ...old, status: data.status }))
    } catch (err) { setError(err.message) } finally { setWorking(false) }
  }

  return <div style={{ display: 'grid', gap: 18 }}>
    <Card title="Pay by bKash / Nagad / Rocket number">
      <p style={{ color: '#475569' }}>
        Send the exact amount to the configured receiving number. After sending,
        enter the transaction ID below. A submitted transaction ID is evidence only;
        payment is confirmed only after provider verification or authorized admin review.
      </p>
      <form onSubmit={createIntent}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
          <label>Provider<select value={provider} onChange={(e) => setProvider(e.target.value)} style={{ width: '100%', padding: 10, marginTop: 5 }}>
            {providers.length === 0 && <option value="bkash">bKash</option>}
            {providers.map((p) => <option key={p} value={p}>{p}</option>)}
          </select></label>
          <label>Amount (BDT)<input value={amount} onChange={(e) => setAmount(e.target.value)} type="number" min="0.01" step="0.01" required style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }} /></label>
          <label>Order ID (optional)<input value={orderId} onChange={(e) => setOrderId(e.target.value)} style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }} /></label>
        </div>
        {selectedAccount && <div style={{ marginTop: 16, padding: 14, borderRadius: 10, background: '#f8fafc' }}>
          <strong>{selectedAccount.display_name}</strong>
          <div>Receiving number: <strong>{selectedAccount.account_number}</strong></div>
          <div>Account type: {selectedAccount.account_type}</div>
          {selectedAccount.instructions && <div style={{ marginTop: 8 }}>{selectedAccount.instructions}</div>}
        </div>}
        {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
        <button disabled={working || !selectedAccount} type="submit" style={{ marginTop: 16, padding: '12px 20px', border: 0, borderRadius: 8, background: '#0ea5e9', color: '#fff', fontWeight: 700 }}>
          {working ? 'Creating payment…' : 'Create payment instructions'}
        </button>
      </form>
    </Card>

    {intent && <Card title="Payment verification">
      <p>Reference: <strong>{intent.expected_reference}</strong></p>
      <p>Amount: <strong>{intent.amount} {intent.currency}</strong></p>
      <p>Send to: <strong>{intent.account?.account_number}</strong></p>
      <p>Status: <strong>{intent.status}</strong></p>
      <form onSubmit={submitPayment}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 14 }}>
          <label>Sender number<input value={senderNumber} onChange={(e) => setSenderNumber(e.target.value)} placeholder="Optional" style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }} /></label>
          <label>Transaction ID / TxID<input value={transactionId} onChange={(e) => setTransactionId(e.target.value)} required style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }} /></label>
          <label>Amount sent<input value={submittedAmount} onChange={(e) => setSubmittedAmount(e.target.value)} type="number" min="0.01" step="0.01" required style={{ width: '100%', padding: 10, marginTop: 5, boxSizing: 'border-box' }} /></label>
        </div>
        {message && <p style={{ color: '#166534' }}>{message}</p>}
        {error && <p style={{ color: '#b91c1c' }}>{error}</p>}
        <button disabled={working} type="submit" style={{ marginTop: 16, padding: '12px 20px', border: 0, borderRadius: 8, background: '#16a34a', color: '#fff', fontWeight: 700 }}>
          {working ? 'Submitting…' : 'Submit payment for verification'}
        </button>
      </form>
    </Card>}
  </div>
}
