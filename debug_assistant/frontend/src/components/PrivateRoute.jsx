/**
 * components/PrivateRoute.jsx — Redirect to /login if not authenticated.
 */
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth.js'

export default function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  return token ? children : <Navigate to="/login" replace />
}
