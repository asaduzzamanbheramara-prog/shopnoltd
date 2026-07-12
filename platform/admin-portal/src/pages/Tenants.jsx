import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Tenants() {
  const { data } = useQuery({ queryKey: ['tenants'], queryFn: () => api.get('/tenants').then(r => r.data) })
  return <div><h1>Tenants</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
