import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Payments() {
  const { data, isLoading } = useQuery({ queryKey: ['pending'], queryFn: () => api.get('/admin/pending').then(r => r.data) })
  return (
    <div>
      <h1>Pending Approvals</h1>
      {isLoading ? <p>Loading…</p> : (
        <pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  )
}
