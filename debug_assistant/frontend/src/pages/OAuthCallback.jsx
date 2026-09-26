import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import api from '../api.js'
import { useAuthStore } from '../store/auth.js'
import { ShieldCheck, AlertCircle } from 'lucide-react'

export default function OAuthCallback() {
  const [searchParams] = useSearchParams()
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()

  useEffect(() => {
    const token = searchParams.get('token') || searchParams.get('oauth_token')
    const err = searchParams.get('error')

    if (err) {
      setError(decodeURIComponent(err))
      return
    }

    if (!token) {
      setError('No authentication token received from OAuth provider.')
      return
    }

    // Fetch authenticated user profile using token
    api.get('/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        setAuth(token, res.data)
        navigate('/dashboard', { replace: true })
      })
      .catch((err) => {
        setError(err.response?.data?.detail ?? 'Failed to verify OAuth credentials')
      })
  }, [searchParams, setAuth, navigate])

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="bg-white/90 backdrop-blur-md border border-slate-200/80 rounded-2xl p-8 max-w-md w-full text-center shadow-card">
        {error ? (
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-full bg-rose-50 border border-rose-200 text-rose-600 mx-auto flex items-center justify-center">
              <AlertCircle className="w-6 h-6" />
            </div>
            <h2 className="text-base font-bold text-slate-900">OAuth Authentication Error</h2>
            <p className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-xl p-3 font-medium">
              {error}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="mt-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition-all"
            >
              Return to Sign In
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="w-12 h-12 rounded-full bg-blue-50 border border-blue-200 text-blue-600 mx-auto flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 animate-pulse" />
            </div>
            <h2 className="text-base font-bold text-slate-900">Finalizing Secure OAuth Sign-In</h2>
            <p className="text-xs text-slate-500">
              Validating session and synchronizing developer workspace...
            </p>
            <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mt-2" />
          </div>
        )}
      </div>
    </div>
  )
}
