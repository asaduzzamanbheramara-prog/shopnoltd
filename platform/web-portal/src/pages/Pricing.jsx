import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
export default function Pricing() {
  const navigate = useNavigate()
  const plans = [
    { name: 'Free',    price: 0,    features: ['1 user', '1 GB storage', 'Community support'] },
    { name: 'Starter', price: 9,    features: ['5 users', '50 GB storage', 'Email support'] },
    { name: 'Pro',     price: 29,   features: ['25 users', '500 GB storage', 'Priority support'] },
    { name: 'Business',price: 99,   features: ['100 users', '5 TB storage', '24/7 support'] },
    { name: 'Enterprise', price: 299, features: ['Unlimited users', 'Unlimited storage', 'Dedicated success manager'] },
  ]
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Shopnoltd Pricing &amp; Plans</h1>
      <p style={{ maxWidth: 820, margin: '0 auto 16px', color: '#334155', lineHeight: 1.7 }}>
        Compare the listed Shopnoltd plans by team size, storage allowance, and support needs. The plan cards below show the monthly prices and included features for each option, from the Free plan through Enterprise.
      </p>
      <p style={{ maxWidth: 820, margin: '0 auto 24px', color: '#334155', lineHeight: 1.7 }}>
        Choose the option that best fits your current needs to continue to checkout and review the selected plan before payment. You can also explore <Link to="/services">Shopnoltd services</Link> or <Link to="/contact">contact us</Link> if you need help understanding which option is right for you.
      </p>
      <h2 style={{ fontSize: 20, marginBottom: 16 }}>Compare plans by team, storage, and support</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {plans.map(p => (
          <div key={p.name} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2>{p.name}</h2>
            <p style={{ fontSize: 36, fontWeight: 700 }}>${p.price}<span style={{ fontSize: 14, color: '#64748b' }}>/mo</span></p>
            <ul>{p.features.map(f => <li key={f}>{f}</li>)}</ul>
            <button
                onClick={() => navigate(`/checkout?plan=${p.name.toLowerCase()}`)}
                style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8, cursor: 'pointer' }}
              >
                Choose
              </button>
          </div>
        ))}
      </div>
    </div>
  )
}
