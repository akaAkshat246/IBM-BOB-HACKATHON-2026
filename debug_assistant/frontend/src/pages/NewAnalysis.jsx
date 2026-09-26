import { useState, useMemo, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import api from '../api.js'
import Layout from '../components/Layout.jsx'
import {
  Terminal,
  Zap,
  Sliders,
  FolderGit2,
  ArrowRight,
  FileCode2,
  AlertCircle,
  CheckCircle2,
  Plus
} from 'lucide-react'

const PRESETS = [
  {
    id: 'keyerror',
    name: 'Python KeyError',
    desc: 'Propagated dict key mismatch',
    title: 'KeyError: price in pricing.py',
    repo: 'sample_repo',
    depth: 10,
    traceback: `Traceback (most recent call last):
  File "sample_repo/app.py", line 42, in handle_request
    result = process_order(request.data)
  File "sample_repo/orders.py", line 18, in process_order
    total = calculate_total(order["items"])
  File "sample_repo/pricing.py", line 31, in calculate_total
    unit_price = item["price"]
KeyError: 'price'`,
  },
  {
    id: 'java_npe',
    name: 'Java NullPointer',
    desc: 'Spring Boot unvalidated entity',
    title: 'NullPointerException in OrderProcessor',
    repo: 'sample_repo',
    depth: 8,
    traceback: `java.lang.NullPointerException: Cannot invoke "Customer.getId()" because "order.customer" is null
    at com.enterprise.orders.OrderProcessor.validateOrder(OrderProcessor.java:84)
    at com.enterprise.orders.OrderService.submit(OrderService.java:122)
    at com.enterprise.api.OrderController.handleCreate(OrderController.java:45)`,
  },
  {
    id: 'node_type',
    name: 'Node.js TypeError',
    desc: 'Express async handler fault',
    title: 'TypeError in billing service',
    repo: 'sample_repo',
    depth: 6,
    traceback: `TypeError: Cannot read properties of undefined (reading 'tier')
    at calculateDiscount (src/services/billing.js:28:22)
    at checkoutOrder (src/controllers/orderController.js:64:18)
    at Layer.handle [as handle_request] (node_modules/express/lib/router/layer.js:95:5)`,
  },
]

export default function NewAnalysis() {
  const location = useLocation()
  const [form, setForm] = useState({
    title: location.state?.title || 'KeyError: price in pricing.py',
    traceback_text: PRESETS[0].traceback,
    repo_path: location.state?.repo_path || 'sample_repo',
    max_depth: 10,
  })
  const [connectedRepos, setConnectedRepos] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // Fetch connected repos
    api.get('/repos')
      .then((res) => setConnectedRepos(res.data))
      .catch(() => {})
  }, [])

  // Real-time error signature detector preview
  const detectedSignature = useMemo(() => {
    const text = form.traceback_text.trim()
    if (!text) return null

    // Match python exception
    const pyMatch = text.match(/([a-zA-Z_]\w*(?:Error|Exception|Warning)):\s*(.*)$/m)
    if (pyMatch) {
      return { type: pyMatch[1], message: pyMatch[2] || '(no message)' }
    }
    // Match Java
    const javaMatch = text.match(/([\w.$]+(?:Exception|Error)):\s*(.*)$/m)
    if (javaMatch) {
      return { type: javaMatch[1], message: javaMatch[2] || '(no message)' }
    }
    // Match Node
    const nodeMatch = text.match(/^(TypeError|ReferenceError|RangeError|SyntaxError):\s*(.*)$/m)
    if (nodeMatch) {
      return { type: nodeMatch[1], message: nodeMatch[2] || '(no message)' }
    }
    return null
  }, [form.traceback_text])

  const applyPreset = (preset) => {
    setForm({
      ...form,
      title: preset.title,
      traceback_text: preset.traceback,
      repo_path: preset.repo,
      max_depth: preset.depth,
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const { data } = await api.post('/analyses', {
        ...form,
        max_depth: Number(form.max_depth),
      })
      navigate(`/report/${data.id}`)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to initiate root cause trace')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Page Header */}
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            New Root-Cause Trace Analysis
          </h1>
          <p className="text-xs text-slate-500 mt-1 font-medium">
            Provide a stack trace from Python, Java, or Node.js. Debug Assistant inspects ASTs, commits, and tests backward from the crash frame.
          </p>
        </div>

        {/* Preset Selector Banner */}
        <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card">
          <div className="flex items-center gap-2 mb-3 text-xs font-bold uppercase tracking-wider text-slate-600">
            <Zap className="w-4 h-4 text-amber-500" />
            <span>Load Preconfigured Test Scenarios</span>
          </div>
          
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {PRESETS.map((p) => {
              const isSelected = form.traceback_text === p.traceback
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => applyPreset(p)}
                  className={`text-left p-3.5 rounded-xl border transition-all ${
                    isSelected
                      ? 'bg-blue-50/80 border-blue-500 shadow-xs'
                      : 'bg-slate-50/70 border-slate-200 hover:border-slate-300 hover:bg-slate-100/70'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{p.name}</span>
                    {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-blue-600" />}
                  </div>
                  <p className="text-[11px] text-slate-500 mt-1 leading-snug font-medium">{p.desc}</p>
                </button>
              )
            })}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="flex items-start gap-2.5 text-xs font-medium text-rose-800 bg-rose-50 border border-rose-200 rounded-xl p-4">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Main Analysis Form */}
        <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-6 shadow-card">
          
          {/* Analysis Title */}
          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
              Trace Title <span className="text-slate-400 font-normal">(Optional Label)</span>
            </label>
            <input
              type="text"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              placeholder="e.g. KeyError in pricing module"
              className="w-full bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all shadow-2xs"
            />
          </div>

          {/* Traceback Editor */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                Crash Traceback / Test Failure Output <span className="text-rose-500">*</span>
              </label>
              {detectedSignature && (
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-blue-50 text-blue-700 border border-blue-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                  Detected: {detectedSignature.type}
                </span>
              )}
            </div>

            <textarea
              required
              rows={11}
              value={form.traceback_text}
              onChange={(e) => setForm({ ...form, traceback_text: e.target.value })}
              placeholder="Paste traceback (Python, Java, or Node.js) here..."
              className="w-full bg-slate-900 text-slate-100 border border-slate-700 rounded-xl p-4 text-xs font-mono placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent leading-relaxed resize-y shadow-inner"
            />
          </div>

          {/* Repository Path & Max Depth */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 pt-1">
            {/* Repo Path */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Repository Path / GitHub URL
                </label>
                <div className="flex gap-1.5">
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, repo_path: 'sample_repo' })}
                    className="text-[10px] font-mono font-bold text-blue-700 hover:text-blue-800 bg-blue-50 px-2 py-0.5 rounded border border-blue-200"
                  >
                    sample_repo
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm({ ...form, repo_path: '.' })}
                    className="text-[10px] font-mono text-slate-600 hover:text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200"
                  >
                    . (cwd)
                  </button>
                </div>
              </div>

              {/* Connected Repos Selector Dropdown */}
              {connectedRepos.length > 0 && (
                <div className="mb-2">
                  <select
                    onChange={(e) => e.target.value && setForm({ ...form, repo_path: e.target.value })}
                    className="w-full bg-slate-50 border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-1 focus:ring-blue-500 font-medium"
                  >
                    <option value="">-- Choose from Connected GitHub Repos --</option>
                    {connectedRepos.map((r) => (
                      <option key={r.id} value={r.local_path}>
                        GitHub: {r.full_name} ({r.default_branch})
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div className="relative">
                <FolderGit2 className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="text"
                  required
                  value={form.repo_path}
                  onChange={(e) => setForm({ ...form, repo_path: e.target.value })}
                  placeholder="sample_repo or https://github.com/owner/repo"
                  className="w-full bg-white border border-slate-300 rounded-xl pl-10 pr-3 py-2.5 text-xs font-mono text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 shadow-2xs"
                />
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500 font-medium">
                Pass a local folder, relative path, or direct GitHub repository clone URL.
              </p>
            </div>

            {/* Depth Slider */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700">
                  Max Trace Depth
                </label>
                <span className="font-mono text-xs text-blue-700 font-bold bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                  {form.max_depth} frames
                </span>
              </div>

              <input
                type="range"
                min={1}
                max={25}
                value={form.max_depth}
                onChange={(e) => setForm({ ...form, max_depth: e.target.value })}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-blue-600 mt-3"
              />
              <div className="flex justify-between text-[10px] text-slate-500 mt-1.5 font-mono">
                <span>1 (Shallow)</span>
                <span>10 (Default)</span>
                <span>25 (Deep Call Tree)</span>
              </div>
            </div>
          </div>

          {/* Form Actions */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-slate-100">
            <button
              type="submit"
              disabled={loading}
              className="flex-1 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white font-semibold py-3 rounded-xl text-sm transition-all shadow-xs flex items-center justify-center gap-2 disabled:opacity-60"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>Launching Autonomous AST Tracers...</span>
                </>
              ) : (
                <>
                  <span>Execute Root-Cause Analysis</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>

            <button
              type="button"
              onClick={() => navigate('/dashboard')}
              className="px-5 py-3 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-xl transition-all"
            >
              Cancel
            </button>
          </div>

        </form>

      </div>
    </Layout>
  )
}
