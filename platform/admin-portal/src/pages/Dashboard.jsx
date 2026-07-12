import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ['services'], queryFn: () => api.get('/services').then(r => r.data) })
  if (isLoading) return <p>Loading…</p>
  const entries = Object.entries(data || {})
  return (
    <div>
      <h1>Cluster Health</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 16 }}>
        {entries.map(([name, status]) => (
          <div key={name} style={{ background: 'white', padding: 20, borderRadius: 12, boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <h3 style={{ margin: 0 }}>{name}</h3>
            <p style={{ color: status === 'ok' ? '#10b981' : '#ef4444', fontWeight: 600 }}>{status}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
