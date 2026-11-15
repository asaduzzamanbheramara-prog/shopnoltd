import { Navigate } from 'react-router-dom'
import { isPlatformAdmin } from '../lib/jwt'

export default function AdminRoute({ children }) {
  const token = localStorage.getItem('shopno_token')

  // Not authenticated.
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // Authenticated but not a platform administrator.
  // This matches the backend platform_admin-only authorization policy.
  if (!isPlatformAdmin()) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
