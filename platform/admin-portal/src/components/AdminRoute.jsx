import { Navigate, useLocation } from 'react-router-dom'
import { isPlatformAdmin } from '../lib/jwt'
export default function AdminRoute({ children }) {
  const token = localStorage.getItem('shopno_token'); const location = useLocation()
  if (!token) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname + location.search)}`} replace />
  if (!isPlatformAdmin()) return <Navigate to="/forbidden" replace />
  return children
}
