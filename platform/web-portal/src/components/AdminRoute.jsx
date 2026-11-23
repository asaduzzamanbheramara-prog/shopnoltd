import { Navigate } from 'react-router-dom'
import { isPlatformAdmin, isTenantOwner } from '../lib/jwt'

export default function AdminRoute({ children, allowTenantOwner = false }) {
  const token = localStorage.getItem('shopno_token')

  // Not authenticated.
  if (!token) {
    return <Navigate to="/login" replace />
  }

  // Platform administration stays platform_admin-only. Individual tenant
  // management pages may explicitly opt in to the canonical tenant_owner role.
  if (!isPlatformAdmin() && !(allowTenantOwner && isTenantOwner())) {
    return <Navigate to="/dashboard" replace />
  }

  return children
}
