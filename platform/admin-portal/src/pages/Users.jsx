import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Users() {
  const { data, isLoading } = useQuery({ queryKey: ['users'], queryFn: () => api.get('/users').then(r => r.data) })
  if (isLoading) return <p>Loading…</p>
  return (
    <div>
      <h1>Users</h1>
      <table style={{ width: '100%', background: 'white', borderRadius: 12, overflow: 'hidden' }}>
        <thead style={{ background: '#0f172a', color: 'white' }}>
          <tr><th>Email</th><th>Name</th><th>Tenant</th><th>Roles</th></tr>
        </thead>
        <tbody>
          {(data || []).map(u => (
            <tr key={u.id} style={{ borderBottom: '1px solid #e2e8f0' }}>
              <td style={{ padding: 12 }}>{u.email}</td><td>{u.name}</td><td>{u.tenant_id}</td><td>{(u.roles || []).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
