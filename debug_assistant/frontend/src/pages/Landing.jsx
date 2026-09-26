import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth.js'
import {
  ArrowRight,
  ShieldCheck,
  Zap,
  Terminal,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  Layers,
  Code2,
  FolderGit2,
  TestTube2,
  Activity,
  Sparkles,
  Search,
  ExternalLink,
  ChevronRight,
  AlertTriangle,
  Play
} from 'lucide-react'

export default function Landing() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [selectedDemo, setSelectedDemo] = useState('python')

  const demos = {
    python: {
      title: 'Python KeyError in Order Pricing',
      exception: 'KeyError: "price"',
      crash: 'sample_repo/pricing.py:31 (calculate_total)',
      rootCause: 'sample_repo/app.py:42 (handle_request)',
      frames: [
        { num: 1, file: 'sample_repo/pricing.py:31', func: 'calculate_total', note: 'Crash site: unit_price = item["price"] fails on unvalidated dict key' },
        { num: 2, file: 'sample_repo/orders.py:18', func: 'process_order', note: 'Propagated unvalidated payload items list downstream' },
        { num: 3, file: 'sample_repo/app.py:42', func: 'handle_request', note: 'Root Origin: Request data parsed without default key normalization', isRC: true },
      ],
      patch: `--- sample_repo/pricing.py
+++ sample_repo/pricing.py
@@ -30,2 +30,2 @@
-    unit_price = item["price"]
+    unit_price = item.get("price", 0.0)`
    },
    java: {
      title: 'Java NullPointerException in Spring OrderProcessor',
      exception: 'NullPointerException: Cannot invoke "Customer.getId()"',
      crash: 'OrderProcessor.java:84 (validateOrder)',
      rootCause: 'OrderController.java:45 (handleCreate)',
      frames: [
        { num: 1, file: 'OrderProcessor.java:84', func: 'validateOrder', note: 'Crash site: order.customer is null on getter invocation' },
        { num: 2, file: 'OrderService.java:122', func: 'submit', note: 'Passed raw DTO into validation pipeline without null-check' },
        { num: 3, file: 'OrderController.java:45', func: 'handleCreate', note: 'Root Origin: Customer object omitted in request payload body', isRC: true },
      ],
      patch: `--- OrderProcessor.java
+++ OrderProcessor.java
@@ -83,2 +83,4 @@
+    if (order.getCustomer() == null) {
+        throw new InvalidOrderException("Customer information is required");
+    }`
    }
  }

  const current = demos[selectedDemo]

  return (
    <div className="min-h-screen text-slate-800 font-sans flex flex-col">
      
      {/* Top Navbar */}
      <header className="bg-white/85 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-3">
            <img
              src="/ibm-bob-logo.png"
              alt="Debug Assistant Logo"
              className="w-9 h-9 rounded-lg border border-slate-200 object-contain p-0.5 shadow-xs"
            />
            <span className="font-bold tracking-tight text-slate-900 text-base">
              Debug Assistant
            </span>
          </Link>

          <div className="flex items-center gap-3">
            {user ? (
              <Link
                to="/dashboard"
                className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-xs transition-all"
              >
                <span>Go to Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-xs font-semibold text-slate-600 hover:text-slate-900 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors"
                >
                  Sign In
                </Link>
                <Link
                  to="/login"
                  className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white text-xs font-semibold px-4 py-2 rounded-lg shadow-xs transition-all"
                >
                  <span>Launch Workspace</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="bg-white/70 backdrop-blur-sm border-b border-slate-200/80 py-16 sm:py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto text-center space-y-6">
          
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 text-xs font-semibold shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-blue-600 animate-pulse" />
            <span>Deterministic AST Call-Tree Tracer</span>
          </div>

          <h1 className="text-3xl sm:text-5xl font-extrabold tracking-tight text-slate-900 leading-tight">
            Stop Guessing Where Bugs Start.<br />
            <span className="text-blue-600">Trace the True Root Cause in Seconds.</span>
          </h1>

          <p className="text-base sm:text-lg text-slate-600 max-w-3xl mx-auto leading-relaxed font-normal">
            When an application crashes, stack traces only tell you where it died, not where the faulty data was introduced. 
            <strong> Debug Assistant</strong> walks backward along the call tree, correlates commit history and test gaps with parallel subagents, and generates verified fixes automatically.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
            <Link
              to="/new"
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm px-6 py-3.5 rounded-xl shadow-card transition-all"
            >
              <Terminal className="w-4 h-4" />
              <span>Start an Analysis</span>
            </Link>
            <Link
              to="/login"
              className="w-full sm:w-auto flex items-center justify-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-800 font-semibold text-sm px-6 py-3.5 rounded-xl border border-slate-200 transition-all"
            >
              <Zap className="w-4 h-4 text-amber-500" />
              <span>1-Click Demo Login</span>
            </Link>
          </div>

          {/* Value Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-8 max-w-3xl mx-auto text-left">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-xs font-bold text-slate-900 block">Deterministic AST</span>
              <span className="text-[11px] text-slate-500 font-medium">Zero LLM hallucinations</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-xs font-bold text-slate-900 block">Parallel Subagents</span>
              <span className="text-[11px] text-slate-500 font-medium">Git blame, issues, tests</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-xs font-bold text-slate-900 block">Multi-Language</span>
              <span className="text-[11px] text-slate-500 font-medium">Python, Java, Node.js</span>
            </div>
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl">
              <span className="text-xs font-bold text-slate-900 block">Mean Latency &lt;0.3s</span>
              <span className="text-[11px] text-slate-500 font-medium">Instant speed</span>
            </div>
          </div>

        </div>
      </section>

      {/* How It Works Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full space-y-12">
        <div className="text-center space-y-2">
          <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
            Engineered Architecture
          </span>
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
            How Debug Assistant Resolves the Bug Origin
          </h2>
          <p className="text-sm text-slate-500 max-w-2xl mx-auto font-medium">
            Four specialized stages turn a noisy crash traceback into an actionable engineering patch.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
          
          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-card space-y-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center text-blue-600 font-bold text-sm">
              1
            </div>
            <h3 className="text-base font-bold text-slate-900">Traceback Intake</h3>
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Accepts crash outputs from Python tracebacks, Java JVM exceptions, or Node.js error stacks. Normalizes frames and extracts crash line references.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-card space-y-3">
            <div className="w-10 h-10 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600 font-bold text-sm">
              2
            </div>
            <h3 className="text-base font-bold text-slate-900">AST Upstream Tracer</h3>
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Walks upstream frame-by-frame along the repository source tree. Inspects variable assignments and argument propagation to pinpoint the exact root cause frame.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-card space-y-3">
            <div className="w-10 h-10 rounded-xl bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 font-bold text-sm">
              3
            </div>
            <h3 className="text-base font-bold text-slate-900">Parallel Subagents</h3>
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Three specialized subagents run concurrently: <strong>Git Blame</strong> analyzes recent commit history, <strong>Issue Matcher</strong> correlates bug trackers, and <strong>Test Coverage</strong> surfaces uncovered logic paths.
            </p>
          </div>

          <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-card space-y-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 font-bold text-sm">
              4
            </div>
            <h3 className="text-base font-bold text-slate-900">Synthesis & Remediation</h3>
            <p className="text-xs text-slate-600 leading-relaxed font-medium">
              Produces a structured report with confidence metrics, a unified Git remediation diff, and a synthesized Pytest/Unittest regression test case.
            </p>
          </div>

        </div>
      </section>

      {/* Interactive Live Sandbox Preview */}
      <section className="bg-white/70 backdrop-blur-sm border-y border-slate-200/80 py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto space-y-8">
          
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
            <div>
              <span className="text-xs font-bold uppercase tracking-wider text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-200">
                Interactive Preview
              </span>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 mt-2">
                See Root-Cause Causation in Action
              </h2>
              <p className="text-xs text-slate-500 font-medium mt-1">
                Select a test scenario below to explore the backward causation tree and synthesized patch.
              </p>
            </div>

            <div className="flex items-center gap-2 p-1 bg-slate-100 border border-slate-200 rounded-xl">
              <button
                onClick={() => setSelectedDemo('python')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedDemo === 'python'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Python KeyError Scenario
              </button>
              <button
                onClick={() => setSelectedDemo('java')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  selectedDemo === 'java'
                    ? 'bg-white text-blue-700 shadow-xs'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Java NullPointer Scenario
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            
            {/* Left: Causation Flow Timeline */}
            <div className="lg:col-span-7 bg-slate-50 border border-slate-200 rounded-2xl p-6 space-y-4 shadow-card">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  Causation Propagation Chain
                </span>
                <span className="text-xs font-mono font-bold text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded border border-rose-200">
                  {current.exception}
                </span>
              </div>

              <div className="space-y-3">
                {current.frames.map((f, idx) => (
                  <div
                    key={idx}
                    className={`p-4 rounded-xl border bg-white transition-all shadow-xs ${
                      f.isRC
                        ? 'border-rose-300 ring-2 ring-rose-100'
                        : 'border-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <div className="flex items-center gap-2">
                        <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                          f.isRC ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-700 border border-slate-200'
                        }`}>
                          {f.isRC ? 'ROOT CAUSE ORIGIN' : `Frame ${f.num}`}
                        </span>
                        <span className="font-mono font-bold text-xs text-slate-900">{f.func}</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-500">{f.file}</span>
                    </div>
                    <p className="text-xs text-slate-600 font-medium">{f.note}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: Remediation Diff */}
            <div className="lg:col-span-5 bg-slate-900 border border-slate-800 rounded-2xl p-6 text-slate-100 shadow-card space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="text-xs font-bold text-blue-400 uppercase tracking-wider flex items-center gap-1.5">
                  <GitCommit className="w-4 h-4" /> Synthesized Remediation Diff
                </span>
                <span className="text-[10px] font-mono bg-blue-950 text-blue-300 px-2 py-0.5 rounded border border-blue-800">
                  AST Verified
                </span>
              </div>

              <pre className="text-xs font-mono text-slate-200 bg-slate-950 p-4 rounded-xl border border-slate-800 overflow-x-auto leading-relaxed report-scroll">
                {current.patch.split('\n').map((line, i) => {
                  let cls = 'text-slate-300'
                  if (line.startsWith('+') && !line.startsWith('+++')) cls = 'text-emerald-400 font-semibold'
                  if (line.startsWith('-') && !line.startsWith('---')) cls = 'text-rose-400 font-semibold'
                  if (line.startsWith('@@')) cls = 'text-blue-400 font-bold'
                  return <div key={i} className={cls}>{line}</div>
                })}
              </pre>

              <div className="p-3 bg-slate-800/80 rounded-xl text-xs text-slate-300 font-medium leading-relaxed">
                Debug Assistant isolated the unvalidated assignment in <strong>{current.rootCause}</strong> and automatically generated the defensive patch above.
              </div>

              <Link
                to="/new"
                className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs py-2.5 rounded-xl shadow-xs transition-all"
              >
                <span>Run Full Trace on Your Repository</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

          </div>

        </div>
      </section>

      {/* Footer */}
      <footer className="bg-white/85 backdrop-blur-md border-t border-slate-200/80 py-8 px-4 sm:px-6 lg:px-8 mt-auto text-slate-500 text-xs">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-slate-600">
            <img src="/ibm-bob-logo.png" alt="Debug Assistant" className="w-5 h-5 rounded object-contain" />
            <span className="font-semibold text-slate-800">Debug Assistant</span>
            <span>• Production Build</span>
          </div>
          <div className="flex items-center gap-4 text-slate-600 font-medium">
            <Link to="/login" className="hover:text-blue-600 transition-colors">Sign In</Link>
            <span>•</span>
            <Link to="/register" className="hover:text-blue-600 transition-colors">Register</Link>
            <span>•</span>
            <Link to="/dashboard" className="hover:text-blue-600 transition-colors">Dashboard</Link>
          </div>
        </div>
      </footer>

    </div>
  )
}
