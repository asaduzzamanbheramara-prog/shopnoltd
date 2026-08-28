import { Navigate } from 'react-router-dom'
import { getRoles } from '../lib/jwt'

export default function AdminRoute({ children }) {
  const token = localStorage.getItem('shopno_token')

  // Not authenticated.
  if (!token) {
    return <Navigate to="/login" replace />
  }

  const roles = getRoles()

  // Authenticated but not a platform administrator.
  if (!roles.includes('platform_admin')) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
