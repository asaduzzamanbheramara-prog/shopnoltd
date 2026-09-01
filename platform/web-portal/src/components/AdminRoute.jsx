import { Navigate } from 'react-router-dom'
import { isPlatformAdmin } from '../lib/jwt'

export default function AdminRoute({ children }) {
  const token = localStorage.getItem('shopno_token')

  // Not authenticated.
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // Authenticated but not a platform administrator.
  // Uses the same check as the nav bar (accepts 'platform_admin' OR 'admin')
  // so anyone who sees the Admin link can actually open it.
  if (!isPlatformAdmin()) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
