import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/auth.js'
import { PlusCircle, LayoutDashboard, LogOut, ShieldCheck, FolderGit2 } from 'lucide-react'

export default function Layout({ children }) {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const isActive = (path) => location.pathname === path

  return (
    <div className="min-h-screen text-slate-800 flex flex-col font-sans">
      
      {/* Top Navigation Bar */}
      <header className="bg-white/85 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          
          {/* Logo & Product Title */}
          <div className="flex items-center gap-6">
            <Link to="/dashboard" className="flex items-center gap-3 group">
              <img
                src="/ibm-bob-logo.png"
                alt="Debug Assistant Logo"
                className="w-9 h-9 rounded-lg border border-slate-200 object-contain p-0.5 shadow-xs group-hover:border-blue-500 transition-all"
              />
              <div className="flex flex-col">
                <span className="font-bold tracking-tight text-slate-900 text-base">
                  Debug Assistant
                </span>
                <span className="text-[11px] text-slate-500 font-medium">
                  Root-Cause Intelligence
                </span>
              </div>
            </Link>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center gap-1.5 ml-4 border-l border-slate-200 pl-4">
              <Link
                to="/dashboard"
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive('/dashboard')
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>
              <Link
                to="/repos"
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive('/repos')
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <FolderGit2 className="w-4 h-4" />
                <span>GitHub Repos</span>
              </Link>
              <Link
                to="/new"
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  isActive('/new')
                    ? 'bg-blue-50 text-blue-700 border border-blue-200'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
                }`}
              >
                <PlusCircle className="w-4 h-4" />
                <span>New Analysis</span>
              </Link>
            </nav>
          </div>

          {/* Right Controls: New Analysis & User Menu */}
          <div className="flex items-center gap-3">
            
            {/* New Analysis Primary Button */}
            <Link
              to="/new"
              className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold px-3.5 py-2 rounded-lg shadow-xs transition-all"
            >
              <PlusCircle className="w-4 h-4" />
              <span className="hidden sm:inline">New Trace</span>
            </Link>


            {/* User Profile & Sign out */}
            {user && (
              <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
                <div className="hidden lg:flex flex-col text-right">
                  <div className="flex items-center gap-1.5 justify-end">
                    <span className="text-xs font-semibold text-slate-800">{user.username}</span>
                    {user.provider && user.provider !== 'local' && (
                      <span className="text-[9px] uppercase font-bold px-1 rounded bg-slate-100 text-slate-600 border border-slate-200">
                        {user.provider}
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500">{user.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  title="Sign out"
                  className="p-1.5 text-slate-500 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors border border-transparent hover:border-rose-200"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>

        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Clean Light Footer */}
      <footer className="bg-white/85 backdrop-blur-md border-t border-slate-200/80 py-6 text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-slate-600">
            <img src="/ibm-bob-logo.png" alt="Debug Assistant" className="w-5 h-5 rounded object-contain" />
            <span className="font-medium">Debug Assistant • Deterministic Root-Cause Intelligence</span>
          </div>
          <div className="flex items-center gap-4 text-slate-500">
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              AST Engine: Active
            </span>
            <span className="hidden md:inline text-slate-300">|</span>
            <span className="flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-blue-600" />
              Production Ready
            </span>
          </div>
        </div>
      </footer>

    </div>
  )
}
