import { useEffect, useState, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api.js'
import Layout from '../components/Layout.jsx'
import {
  FolderGit2,
  PlusCircle,
  RotateCw,
  Trash2,
  Play,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  Zap,
  AlertCircle,
  GitBranch,
  Clock
} from 'lucide-react'

function fmt(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function Repositories() {
  const [repos, setRepos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({ url: '', branch: 'main', token: '' })
  const [connecting, setConnecting] = useState(false)
  const [syncingId, setSyncingId] = useState(null)
  const navigate = useNavigate()

  const fetchRepos = useCallback(async () => {
    try {
      const { data } = await api.get('/repos')
      setRepos(data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to load connected repositories')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchRepos()
  }, [fetchRepos])

  const handleConnect = async (e) => {
    e.preventDefault()
    if (!form.url.trim()) return
    setError('')
    setConnecting(true)
    try {
      const { data } = await api.post('/repos/connect', form)
      setRepos((prev) => [data, ...prev.filter((r) => r.id !== data.id)])
      setForm({ url: '', branch: 'main', token: '' })
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to connect repository')
    } finally {
      setConnecting(false)
    }
  }

  const handleSync = async (id) => {
    setSyncingId(id)
    try {
      const { data } = await api.post(`/repos/${id}/sync`)
      setRepos((prev) => prev.map((r) => (r.id === id ? data : r)))
    } catch (err) {
      alert('Sync failed: ' + (err.response?.data?.detail ?? err.message))
    } finally {
      setSyncingId(null)
    }
  }

  const handleDisconnect = async (id) => {
    if (!window.confirm('Disconnect this repository from your workspace?')) return
    try {
      await api.delete(`/repos/${id}`)
      setRepos((prev) => prev.filter((r) => r.id !== id))
    } catch (err) {
      alert('Disconnect failed: ' + (err.response?.data?.detail ?? err.message))
    }
  }

  const quickConnectPreset = (url) => {
    setForm({ ...form, url })
  }

  return (
    <Layout>
      <div className="space-y-6 max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Connected GitHub Repositories
            </h1>
            <p className="text-xs text-slate-500 mt-1 font-medium">
              Manage local repository workspaces for deterministic AST call-tree tracing and subagent synthesis.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchRepos()}
              className="p-2 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg shadow-xs transition-all"
              title="Refresh"
            >
              <RotateCw className="w-4 h-4" />
            </button>
            <Link
              to="/new"
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-xs transition-all"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Launch Analysis</span>
            </Link>
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="text-xs font-medium text-rose-800 bg-rose-50 border border-rose-200 rounded-xl p-4 flex items-center gap-2.5">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Connect Repository Card */}
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-7 shadow-card">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-slate-100">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <FolderGit2 className="w-4 h-4 text-blue-600" />
              <span>Connect New GitHub Repository</span>
            </h2>
            <span className="text-[11px] text-blue-700 font-semibold bg-blue-50 border border-blue-200 px-2.5 py-0.5 rounded-full flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 text-blue-600" /> Auto-Clone & AST Index
            </span>
          </div>

          {/* Quick presets */}
          <div className="mb-4">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Quick Suggestions:
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => quickConnectPreset('sample_repo')}
                className="text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors font-mono"
              >
                sample_repo (Built-in)
              </button>
              <button
                type="button"
                onClick={() => quickConnectPreset('https://github.com/pallets/flask')}
                className="text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors font-mono"
              >
                pallets/flask
              </button>
              <button
                type="button"
                onClick={() => quickConnectPreset('https://github.com/fastapi/fastapi')}
                className="text-xs font-semibold text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 px-2.5 py-1 rounded-lg transition-colors font-mono"
              >
                fastapi/fastapi
              </button>
            </div>
          </div>

          <form onSubmit={handleConnect} className="grid grid-cols-1 sm:grid-cols-12 gap-3.5">
            <div className="sm:col-span-6">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Repository URL or owner/repo <span className="text-rose-500">*</span>
              </label>
              <input
                type="text"
                required
                value={form.url}
                onChange={(e) => setForm({ ...form, url: e.target.value })}
                placeholder="https://github.com/owner/repository"
                className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-2xs font-mono"
              />
            </div>

            <div className="sm:col-span-3">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1">
                Default Branch
              </label>
              <input
                type="text"
                value={form.branch}
                onChange={(e) => setForm({ ...form, branch: e.target.value })}
                placeholder="main"
                className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-2xs font-mono"
              />
            </div>

            <div className="sm:col-span-3 flex items-end">
              <button
                type="submit"
                disabled={connecting}
                className="w-full bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-2.5 rounded-xl text-xs transition-all shadow-xs flex items-center justify-center gap-1.5 disabled:opacity-60"
              >
                {connecting ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Connecting...</span>
                  </>
                ) : (
                  <>
                    <PlusCircle className="w-4 h-4" />
                    <span>Connect Repo</span>
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Connected Repositories List */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Connected Repositories ({repos.length})
            </h2>
          </div>

          {loading && (
            <div className="text-center py-16 bg-white border border-slate-200 rounded-2xl shadow-card">
              <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
              <p className="text-xs text-slate-500 font-medium">Loading repository workspaces...</p>
            </div>
          )}

          {!loading && repos.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center shadow-card">
              <FolderGit2 className="w-10 h-10 mx-auto text-slate-400 mb-3" />
              <h3 className="text-base font-bold text-slate-900">No GitHub Repositories Connected</h3>
              <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
                Connect a GitHub repository above to run root-cause analysis against live commits and AST source trees.
              </p>
            </div>
          )}

          {!loading && repos.length > 0 && (
            <div className="space-y-3">
              {repos.map((r) => (
                <div
                  key={r.id}
                  className="bg-white border border-slate-200 rounded-xl p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-card hover:border-slate-300 transition-all"
                >
                  <div className="flex items-start sm:items-center gap-3.5 min-w-0 flex-1">
                    <div className="p-3 bg-slate-100 rounded-xl border border-slate-200 text-slate-700 shrink-0">
                      <svg className="w-5 h-5 fill-current" viewBox="0 0 24 24">
                        <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
                      </svg>
                    </div>

                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-slate-900 font-mono">
                          {r.full_name}
                        </h3>
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <CheckCircle2 className="w-3 h-3" /> Connected
                        </span>
                      </div>

                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500 font-medium">
                        <span className="flex items-center gap-1 font-mono text-slate-600">
                          <GitBranch className="w-3 h-3 text-slate-400" />
                          {r.default_branch}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1 text-slate-500">
                          <Clock className="w-3 h-3 text-slate-400" />
                          Synced {fmt(r.last_synced_at)}
                        </span>
                        <span>•</span>
                        <span className="font-mono text-slate-400 text-[11px]">
                          {r.local_path}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                    <button
                      onClick={() => navigate('/new', { state: { repo_path: r.local_path, title: `Trace in ${r.name}` } })}
                      className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3.5 py-1.5 rounded-lg transition-all"
                    >
                      <Play className="w-3.5 h-3.5" />
                      <span>Run Analysis</span>
                    </button>

                    <button
                      onClick={() => handleSync(r.id)}
                      disabled={syncingId === r.id}
                      className="flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 px-3 py-1.5 rounded-lg transition-all"
                    >
                      <RotateCw className={`w-3.5 h-3.5 ${syncingId === r.id ? 'animate-spin' : ''}`} />
                      <span>{syncingId === r.id ? 'Syncing...' : 'Sync'}</span>
                    </button>

                    <button
                      onClick={() => handleDisconnect(r.id)}
                      title="Disconnect repository"
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 border border-transparent hover:border-rose-200 rounded-lg transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </Layout>
  )
}
