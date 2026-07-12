import { useState } from 'react'
export default function Login() {
  const [email, setEmail] = useState('')
  const [pw, setPw] = useState('')
  async function submit(e) {
    e.preventDefault()
    const r = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: pw }) })
    const d = await r.json()
    if (d.access_token) { localStorage.setItem('shopno_token', d.access_token); window.location.href = '/dashboard' }
  }
  return (
    <form onSubmit={submit} style={{ maxWidth: 360, margin: '64px auto', padding: 24, background: 'white', borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
      <h2>Sign in to Shopnoltd</h2>
      <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" style={{ width: '100%', padding: 10, margin: '8px 0' }} />
      <input type="password" value={pw} onChange={e => setPw(e.target.value)} placeholder="Password" style={{ width: '100%', padding: 10, margin: '8px 0' }} />
      <button style={{ width: '100%', padding: 10, background: '#0ea5e9', color: 'white', border: 0, borderRadius: 8 }}>Sign in</button>
    </form>
  )
}
