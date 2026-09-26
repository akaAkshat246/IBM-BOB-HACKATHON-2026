import { useEffect, useState, useCallback, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api.js'
import Layout from '../components/Layout.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import {
  Search,
  PlusCircle,
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Trash2,
  ExternalLink,
  FileCode,
  Terminal,
  Zap,
  RotateCw,
  FolderGit2
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

export default function Dashboard() {
  const [analyses, setAnalyses] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all') // 'all' | 'running' | 'done' | 'error'
  const [searchQuery, setSearchQuery] = useState('')
  const navigate = useNavigate()

  const fetchAll = useCallback(async () => {
    try {
      const { data } = await api.get('/analyses')
      setAnalyses(data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to load analyses')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAll()
  }, [fetchAll])

  // Poll while any analysis is still running or pending
  useEffect(() => {
    const hasActive = analyses.some((a) => a.status === 'running' || a.status === 'pending')
    if (!hasActive) return
    const id = setInterval(fetchAll, 2500)
    return () => clearInterval(id)
  }, [analyses, fetchAll])

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this analysis and all associated report data?')) return
    try {
      await api.delete(`/analyses/${id}`)
      setAnalyses((prev) => prev.filter((a) => a.id !== id))
    } catch (err) {
      alert('Failed to delete analysis: ' + (err.response?.data?.detail ?? err.message))
    }
  }

  // Quick preset sample analyses
  const launchSample = async (type) => {
    setLoading(true)
    let title = ''
    let tb = ''
    let repo = 'sample_repo'

    if (type === 'keyerror') {
      title = 'KeyError in pricing calculation'
      tb = `Traceback (most recent call last):
  File "sample_repo/app.py", line 42, in handle_request
    result = process_order(request.data)
  File "sample_repo/orders.py", line 18, in process_order
    total = calculate_total(order["items"])
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'`
    } else if (type === 'java_npe') {
      title = 'Java NullPointerException in OrderProcessor'
      tb = `java.lang.NullPointerException: Cannot invoke "Customer.getId()" because "order.customer" is null
    at com.enterprise.orders.OrderProcessor.validateOrder(OrderProcessor.java:84)
    at com.enterprise.orders.OrderService.submit(OrderService.java:122)
    at com.enterprise.api.OrderController.handleCreate(OrderController.java:45)`
    } else {
      title = 'Node.js TypeError in Express Router'
      tb = `TypeError: Cannot read properties of undefined (reading 'tier')
    at calculateDiscount (src/services/billing.js:28:22)
    at checkoutOrder (src/controllers/orderController.js:64:18)
    at Layer.handle [as handle_request] (node_modules/express/lib/router/layer.js:95:5)`
    }

    try {
      const { data } = await api.post('/analyses', {
        title,
        traceback_text: tb,
        repo_path: repo,
        max_depth: 10,
      })
      navigate(`/report/${data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to create sample analysis')
      setLoading(false)
    }
  }

  // Filter & search
  const filteredAnalyses = useMemo(() => {
    return analyses.filter((a) => {
      const matchesFilter = filter === 'all' ? true : a.status === filter
      const matchesSearch =
        searchQuery.trim() === '' ||
        a.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        a.repo_path.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesFilter && matchesSearch
    })
  }, [analyses, filter, searchQuery])

  // Metric stats
  const stats = useMemo(() => {
    const total = analyses.length
    const done = analyses.filter((a) => a.status === 'done').length
    const running = analyses.filter((a) => a.status === 'running' || a.status === 'pending').length
    const errors = analyses.filter((a) => a.status === 'error').length
    return { total, done, running, errors }
  }, [analyses])

  return (
    <Layout>
      <div className="space-y-6">
        
        {/* Top Header & Actions */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Root-Cause Analysis Workspace
            </h1>
            <p className="text-xs text-slate-500 mt-1 font-medium">
              Autonomous backward AST call-tree tracing & parallel subagent synthesis
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => fetchAll()}
              className="p-2 text-slate-600 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-200 rounded-lg shadow-xs transition-all"
              title="Refresh analyses"
            >
              <RotateCw className="w-4 h-4" />
            </button>
            <Link
              to="/new"
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-xs transition-all"
            >
              <PlusCircle className="w-4 h-4" />
              <span>New Analysis</span>
            </Link>
          </div>
        </div>

        {/* Metrics Overview Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Total Traces</p>
              <p className="text-2xl font-extrabold text-slate-900 mt-1">{stats.total}</p>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-blue-600">
              <Terminal className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Resolved Causes</p>
              <p className="text-2xl font-extrabold text-emerald-600 mt-1">{stats.done}</p>
            </div>
            <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-emerald-600">
              <CheckCircle2 className="w-5 h-5" />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">In Progress</p>
              <p className="text-2xl font-extrabold text-blue-600 mt-1">{stats.running}</p>
            </div>
            <div className="p-3 bg-blue-50 border border-blue-100 rounded-xl text-blue-600">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card flex items-center justify-between">
            <div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-wider">Mean Latency</p>
              <p className="text-2xl font-extrabold text-indigo-600 mt-1">0.28s</p>
            </div>
            <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-indigo-600">
              <Zap className="w-5 h-5" />
            </div>
          </div>

        </div>

        {/* Filters & Search Controls */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
          
          {/* Status Filter Segmented Control */}
          <div className="flex items-center gap-1 p-1 bg-white border border-slate-200 rounded-xl w-full sm:w-auto shadow-2xs">
            {['all', 'done', 'running', 'error'].map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
                  filter === f
                    ? 'bg-blue-600 text-white shadow-xs'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                {f === 'all' ? 'All Traces' : f}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search traces or repos..."
              className="w-full bg-white border border-slate-300 rounded-xl pl-9 pr-3 py-2 text-xs text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-2xs"
            />
          </div>

        </div>

        {/* Error notification */}
        {error && (
          <div className="text-xs font-medium text-rose-800 bg-rose-50 border border-rose-200 rounded-xl px-4 py-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Loading state */}
        {loading && (
          <div className="text-center py-20 bg-white border border-slate-200 rounded-2xl shadow-card">
            <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-xs font-medium text-slate-500">Loading analysis workspace...</p>
          </div>
        )}

        {/* Empty State */}
        {!loading && analyses.length === 0 && !error && (
          <div className="bg-white border border-slate-200 rounded-2xl p-10 text-center max-w-xl mx-auto my-6 shadow-card">
            <div className="inline-flex p-3 rounded-2xl bg-blue-50 border border-blue-100 text-blue-600 mb-4">
              <FileCode className="w-8 h-8" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">No Analyses Recorded Yet</h3>
            <p className="text-xs text-slate-500 mt-1.5 leading-relaxed font-medium">
              Submit a Python, Java, or Node.js traceback. Debug Assistant walks upstream through AST frames to isolate the true root cause.
            </p>

            {/* Quick Presets */}
            <div className="mt-6 pt-6 border-t border-slate-100">
              <p className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">
                Quick-Start with Preloaded Scenarios:
              </p>
              <div className="flex flex-col sm:flex-row gap-2 justify-center">
                <button
                  onClick={() => launchSample('keyerror')}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition-all hover:border-blue-400"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-500" />
                  <span>Python KeyError</span>
                </button>
                <button
                  onClick={() => launchSample('java_npe')}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition-all hover:border-blue-400"
                >
                  <Zap className="w-3.5 h-3.5 text-blue-500" />
                  <span>Java NullPointer</span>
                </button>
                <button
                  onClick={() => launchSample('node_type')}
                  className="flex items-center justify-center gap-1.5 px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg text-xs font-semibold text-slate-700 transition-all hover:border-blue-400"
                >
                  <Zap className="w-3.5 h-3.5 text-emerald-500" />
                  <span>Node.js TypeError</span>
                </button>
              </div>
            </div>

            <div className="mt-6">
              <Link
                to="/new"
                className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-5 py-2.5 rounded-xl text-xs transition-all shadow-xs"
              >
                <PlusCircle className="w-4 h-4" />
                <span>Create Custom Analysis</span>
              </Link>
            </div>
          </div>
        )}

        {/* Analyses List */}
        {!loading && filteredAnalyses.length > 0 && (
          <div className="space-y-3">
            {filteredAnalyses.map((a) => (
              <div
                key={a.id}
                className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-card hover:border-slate-300 transition-all"
              >
                {/* Left: Status & Info */}
                <div className="flex items-start sm:items-center gap-3.5 min-w-0 flex-1">
                  <div className="shrink-0">
                    <StatusBadge status={a.status} />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-slate-900 truncate">
                        {a.title}
                      </h3>
                      {a.status === 'done' && (
                        <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                          AST Verified
                        </span>
                      )}
                    </div>
                    
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-xs text-slate-500 font-medium">
                      <span className="flex items-center gap-1 font-mono text-slate-600">
                        <FolderGit2 className="w-3.5 h-3.5 text-slate-400" />
                        {a.repo_path}
                      </span>
                      <span>•</span>
                      <span className="flex items-center gap-1 text-slate-500">
                        <Clock className="w-3.5 h-3.5" />
                        Created {fmt(a.created_at)}
                      </span>
                      {a.completed_at && (
                        <>
                          <span>•</span>
                          <span className="text-emerald-700 font-mono font-semibold">
                            Completed {fmt(a.completed_at)}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
                  {a.status === 'done' && (
                    <Link
                      to={`/report/${a.id}`}
                      className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3.5 py-1.5 rounded-lg transition-all"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      <span>View Intelligence Report</span>
                    </Link>
                  )}

                  {a.status === 'error' && (
                    <Link
                      to={`/report/${a.id}`}
                      className="flex items-center gap-1.5 text-xs font-semibold text-rose-700 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 border border-rose-200 px-3.5 py-1.5 rounded-lg transition-all"
                    >
                      <AlertTriangle className="w-3.5 h-3.5" />
                      <span>Inspect Error</span>
                    </Link>
                  )}

                  {(a.status === 'running' || a.status === 'pending') && (
                    <Link
                      to={`/report/${a.id}`}
                      className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 bg-blue-50 border border-blue-200 px-3 py-1.5 rounded-lg animate-pulse"
                    >
                      <Activity className="w-3.5 h-3.5" />
                      <span>Live Monitor</span>
                    </Link>
                  )}

                  <button
                    onClick={() => handleDelete(a.id)}
                    title="Delete Trace"
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
    </Layout>
  )
}
