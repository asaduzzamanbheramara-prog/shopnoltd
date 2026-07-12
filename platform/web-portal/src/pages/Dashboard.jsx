import { useEffect, useState } from 'react'
export default function Dashboard() {
  const [me, setMe] = useState(null)
  useEffect(() => {
    const t = localStorage.getItem('shopno_token')
    if (!t) return
    fetch('/api/v1/me', { headers: { Authorization: `Bearer ${t}` } }).then(r => r.json()).then(setMe)
  }, [])
  if (!me) return <div style={{ padding: 32 }}>Please log in.</div>
  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: 32, fontFamily: 'system-ui, sans-serif' }}>
      <h1>Welcome, {me.email || me.id}</h1>
      <p>Tenant: {me.tenant_id || 'default'}</p>
      <p>Roles: {(me.roles || []).join(', ')}</p>
    </div>
  )
}
