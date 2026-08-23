import { Navigate } from 'react-router-dom'

export default function ProtectedRoute({ children }) {
  const token = localStorage.getItem('shopno_token')

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return children
}
