import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Plans() {
  const { data } = useQuery({ queryKey: ['plans'], queryFn: () => api.get('/plans').then(r => r.data) })
  return <div><h1>Subscription Plans</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
