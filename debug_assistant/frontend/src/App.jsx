/**
 * App.jsx — React Router setup with Landing Page and Repositories.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import PrivateRoute from './components/PrivateRoute.jsx'
import Landing      from './pages/Landing.jsx'
import Login        from './pages/Login.jsx'
import Register     from './pages/Register.jsx'
import OAuthCallback from './pages/OAuthCallback.jsx'
import Dashboard    from './pages/Dashboard.jsx'
import Repositories from './pages/Repositories.jsx'
import NewAnalysis  from './pages/NewAnalysis.jsx'
import Report       from './pages/Report.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public Landing & Auth */}
        <Route path="/"               element={<Landing />} />
        <Route path="/login"          element={<Login />} />
        <Route path="/register"       element={<Register />} />
        <Route path="/oauth/callback" element={<OAuthCallback />} />


        {/* Protected Dashboard, Repositories & Tracing */}
        <Route path="/dashboard"    element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/repos"        element={<PrivateRoute><Repositories /></PrivateRoute>} />
        <Route path="/new"          element={<PrivateRoute><NewAnalysis /></PrivateRoute>} />
        <Route path="/report/:id"   element={<PrivateRoute><Report /></PrivateRoute>} />

        {/* Default fallback to landing */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
