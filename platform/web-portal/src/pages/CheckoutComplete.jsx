import React, { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { getDeposit } from '../lib/financialApi'
import { trackEvent } from '../lib/analytics'

export default function CheckoutComplete() {
  const { search } = useLocation()
  const ref = new URLSearchParams(search).get('ref')
  const [paymentStatus, setPaymentStatus] = useState('checking')
  useEffect(() => {
    let cancelled = false
    async function verifyPayment() {
      let pending
      try { pending = JSON.parse(sessionStorage.getItem('shopno_pending_checkout') || 'null') } catch { pending = null }
      if (!pending?.transaction_id) {
        if (!cancelled) setPaymentStatus('unverified')
        return
      }
      try {
        let transaction = null
        let status = 'pending'
        for (let attempt = 0; attempt < 5; attempt += 1) {
          transaction = await getDeposit(pending.transaction_id)
          if (cancelled) return
          status = String(transaction?.status || '').toLowerCase()
          if (status === 'completed' || status === 'failed' || status === 'cancelled') break
          if (attempt < 4) await new Promise(resolve => setTimeout(resolve, 2000))
        }
        if (cancelled) return
        setPaymentStatus(status || 'unverified')
        if (status === 'completed') {
          trackEvent('purchase', {
            transaction_id: String(transaction.id || pending.transaction_id),
            currency: String(transaction.currency || pending.currency || 'USD').toUpperCase(),
            value: Number(transaction.amount ?? pending.value),
            method: String(transaction.method || pending.gateway || 'unknown'),
            items: [{ item_id: pending.plan || 'subscription', item_name: String(pending.plan || 'Subscription'), quantity: 1, price: Number(transaction.amount ?? pending.value) }],
          }, { dedupeKey: String(transaction.id || pending.transaction_id) })
          sessionStorage.removeItem('shopno_pending_checkout')
        }
      } catch {
        if (!cancelled) setPaymentStatus('unverified')
      }
    }
    verifyPayment()
    return () => { cancelled = true }
  }, [])
  return <main style={{ maxWidth: 760, margin: '0 auto', padding: 28, fontFamily: 'system-ui, sans-serif' }}>
    <h1>Payment return</h1>
    <p>Your payment provider returned control to Shopnoltd. We check the transaction directly with Shopnoltd before recording a successful purchase.</p>
    <p role="status" aria-live="polite"><strong>Payment status:</strong> {paymentStatus === 'checking' ? 'Checking with payment service…' : paymentStatus === 'completed' ? 'Payment confirmed.' : paymentStatus === 'pending' ? 'Payment is still pending. No purchase has been recorded.' : paymentStatus === 'failed' ? 'Payment failed. No purchase has been recorded.' : 'Unable to verify yet. Check your payment center for the authoritative status.'}</p>
    {ref && <p><b>Reference:</b> {ref}</p>}
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}><Link to="/payments">Payment Center</Link><Link to="/transactions">Transactions</Link><Link to="/wallet">Wallet</Link><Link to="/">Home</Link></div>
  </main>
}
