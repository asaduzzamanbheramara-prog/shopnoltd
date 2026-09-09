import React from 'react'
import { Link, useLocation } from 'react-router-dom'

export default function CheckoutComplete() {
  const { search } = useLocation()
  const ref = new URLSearchParams(search).get('ref')
  return <main style={{ maxWidth: 760, margin: '0 auto', padding: 28, fontFamily: 'system-ui, sans-serif' }}>
    <h1>Payment return</h1>
    <p>Your payment provider returned control to Shopnoltd. The authoritative transaction status is available in the payment center and transaction history.</p>
    {ref && <p><b>Reference:</b> {ref}</p>}
    <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}><Link to="/payments">Payment Center</Link><Link to="/transactions">Transactions</Link><Link to="/wallet">Wallet</Link><Link to="/">Home</Link></div>
  </main>
}
