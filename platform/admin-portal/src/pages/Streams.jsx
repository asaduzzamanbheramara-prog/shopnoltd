import { useQuery } from '@tanstack/react-query'
import { api } from '../api'
export default function Streams() {
  const { data } = useQuery({ queryKey: ['streams'], queryFn: () => api.get('/streams').then(r => r.data) })
  return <div><h1>Live Streams</h1><pre style={{ background: 'white', padding: 20, borderRadius: 12 }}>{JSON.stringify(data, null, 2)}</pre></div>
}
