export default function Pricing() {
  const plans = [
    { name: 'Free',    price: 0,    features: ['1 user', '1 GB storage', 'Community support'] },
    { name: 'Starter', price: 9,    features: ['5 users', '50 GB storage', 'Email support'] },
    { name: 'Pro',     price: 29,   features: ['25 users', '500 GB storage', 'Priority support'] },
    { name: 'Business',price: 99,   features: ['100 users', '5 TB storage', '24/7 support'] },
    { name: 'Enterprise', price: 299, features: ['Unlimited users', 'Unlimited storage', 'Dedicated success manager'] },
  ]
  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Pricing</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16 }}>
        {plans.map(p => (
          <div key={p.name} style={{ padding: 20, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h2>{p.name}</h2>
            <p style={{ fontSize: 36, fontWeight: 700 }}>${p.price}<span style={{ fontSize: 14, color: '#64748b' }}>/mo</span></p>
            <ul>{p.features.map(f => <li key={f}>{f}</li>)}</ul>
            <button style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8 }}>Choose</button>
          </div>
        ))}
      </div>
    </div>
  )
}
