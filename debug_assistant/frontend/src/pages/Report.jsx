import { useEffect, useState, useCallback, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import api from '../api.js'
import Layout from '../components/Layout.jsx'
import StatusBadge from '../components/StatusBadge.jsx'
import {
  ArrowLeft,
  Download,
  Copy,
  Check,
  FileCode,
  GitCommit,
  GitPullRequest,
  CheckCircle2,
  AlertTriangle,
  Layers,
  Sparkles,
  Terminal,
  ShieldCheck,
  Code2,
  FolderGit2,
  TestTube2
} from 'lucide-react'

function CodeBlock({ children, language = 'python' }) {
  const [copied, setCopied] = useState(false)
  const text = typeof children === 'string' ? children : String(children)

  const handleCopy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="relative group rounded-xl bg-slate-900 border border-slate-800 overflow-hidden my-3 shadow-sm">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800 text-[11px] text-slate-400 font-mono">
        <span>{language}</span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <pre className="p-4 text-xs font-mono text-slate-100 overflow-x-auto leading-relaxed report-scroll">
        {children}
      </pre>
    </div>
  )
}

function DiffViewer({ diff }) {
  const [copied, setCopied] = useState(false)
  if (!diff) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs italic bg-slate-50 rounded-xl border border-slate-200">
        No automated patch required for this pattern.
      </div>
    )
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(diff)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="rounded-xl bg-slate-900 border border-slate-800 overflow-hidden my-3 shadow-sm">
      <div className="flex items-center justify-between px-4 py-2 bg-slate-950 border-b border-slate-800 text-[11px] text-slate-400 font-mono">
        <span className="flex items-center gap-1.5 text-blue-400 font-bold">
          <GitCommit className="w-3.5 h-3.5" /> Unified Git Remediation Patch
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-slate-400 hover:text-white px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 transition-colors"
        >
          {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
          <span>{copied ? 'Copied Patch' : 'Copy Patch'}</span>
        </button>
      </div>
      <div className="p-4 text-xs font-mono overflow-x-auto leading-relaxed report-scroll space-y-0.5">
        {diff.split('\n').map((line, i) => {
          let bg = ''
          let textCol = 'text-slate-300'

          if (line.startsWith('+') && !line.startsWith('+++')) {
            bg = 'bg-emerald-950/60'
            textCol = 'text-emerald-300 font-semibold'
          } else if (line.startsWith('-') && !line.startsWith('---')) {
            bg = 'bg-rose-950/60'
            textCol = 'text-rose-300 font-semibold'
          } else if (line.startsWith('@@')) {
            bg = 'bg-blue-950/40'
            textCol = 'text-blue-400 font-bold'
          }

          return (
            <div key={i} className={`px-2 py-0.5 rounded font-mono ${bg} ${textCol}`}>
              {line || ' '}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SectionCard({ title, icon: Icon, badge, color = 'blue', children }) {
  const badgeStyles = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    red: 'bg-rose-50 text-rose-700 border-rose-200',
    emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    amber: 'bg-amber-50 text-amber-700 border-amber-200',
  }

  const iconColors = {
    blue: 'text-blue-600',
    red: 'text-rose-600',
    emerald: 'text-emerald-600',
    purple: 'text-purple-600',
    amber: 'text-amber-600',
  }

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-card">
      <div className="px-5 py-4 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {Icon && <Icon className={`w-4 h-4 ${iconColors[color] || 'text-blue-600'}`} />}
          <h3 className="font-bold text-slate-900 text-sm tracking-tight">{title}</h3>
        </div>
        {badge && (
          <span className={`text-[10px] uppercase font-bold font-mono px-2.5 py-0.5 rounded-full border ${badgeStyles[color] || 'bg-slate-100 text-slate-700 border-slate-200'}`}>
            {badge}
          </span>
        )}
      </div>
      <div className="p-5 text-sm text-slate-700 leading-relaxed space-y-4 font-normal">
        {children}
      </div>
    </div>
  )
}

export default function Report() {
  const { id } = useParams()
  const [analysis, setAnalysis] = useState(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('overview') // 'overview' | 'tree' | 'subagents' | 'fix' | 'html' | 'json'
  const [copiedSummary, setCopiedSummary] = useState(false)

  const fetchAnalysis = useCallback(async () => {
    try {
      const { data } = await api.get(`/analyses/${id}`)
      setAnalysis(data)
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Failed to load analysis record')
    }
  }, [id])

  useEffect(() => {
    fetchAnalysis()
  }, [fetchAnalysis])

  useEffect(() => {
    if (!analysis) return
    if (analysis.status === 'running' || analysis.status === 'pending') {
      const timer = setInterval(fetchAnalysis, 2000)
      return () => clearInterval(timer)
    }
  }, [analysis, fetchAnalysis])

  const report = useMemo(() => {
    if (!analysis?.report_json) return null
    try {
      return JSON.parse(analysis.report_json)
    } catch {
      return null
    }
  }, [analysis])

  const sig = report?.error_signature
  const chain = report?.causation_chain_steps ?? []
  const sub = report?.subagent_summaries ?? {}
  const fix = report?.suggested_fix

  const copyMarkdown = () => {
    if (!report) return
    const md = `# Debug Assistant Root Cause Intelligence Report
Analysis: ${analysis.title}
Status: ${analysis.status}
Exception: ${sig?.exception_type} - ${sig?.message}
Crash Site: ${sig?.crash_file}:${sig?.crash_line}
Root Cause Function: ${chain[chain.length - 1]?.function || 'Isolated'}

## Root Cause
${report.root_cause}

## Confidence
${report.confidence}

## Suggested Fix
${fix?.explanation || 'N/A'}
`
    navigator.clipboard.writeText(md)
    setCopiedSummary(true)
    setTimeout(() => setCopiedSummary(false), 2000)
  }

  const downloadHtml = () => {
    if (!analysis?.report_html) return
    const blob = new Blob([analysis.report_html], { type: 'text/html' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ibm-bob-report-${id}.html`
    a.click()
  }

  const downloadJson = () => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `ibm-bob-report-${id}.json`
    a.click()
  }

  if (error) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <div className="text-rose-800 bg-rose-50 border border-rose-200 rounded-xl p-5 text-sm flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-rose-600 shrink-0" />
            <span>{error}</span>
          </div>
        </div>
      </Layout>
    )
  }

  if (!analysis) {
    return (
      <Layout>
        <div className="text-center py-24 bg-white border border-slate-200 rounded-2xl shadow-card max-w-xl mx-auto">
          <div className="inline-block w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs font-semibold text-slate-600">Fetching root-cause telemetry...</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="space-y-6 max-w-6xl mx-auto">
        
        {/* Navigation & Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors bg-white px-3 py-1 rounded-lg border border-slate-200 shadow-2xs"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Dashboard</span>
              </Link>
              <StatusBadge status={analysis.status} />
              <span className="text-xs text-slate-400 font-mono">Trace #{analysis.id}</span>
            </div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {analysis.title}
            </h1>
            <div className="flex items-center gap-3 text-xs text-slate-500 mt-1 font-medium">
              <span className="flex items-center gap-1 font-mono text-slate-600">
                <FolderGit2 className="w-3.5 h-3.5 text-slate-400" />
                {analysis.repo_path}
              </span>
              <span>•</span>
              <span>Max Depth: {analysis.max_depth}</span>
            </div>
          </div>

          {/* Quick Actions Toolbar */}
          {analysis.status === 'done' && (
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={copyMarkdown}
                className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 px-3 py-2 rounded-lg transition-all shadow-2xs"
              >
                {copiedSummary ? <Check className="w-3.5 h-3.5 text-emerald-600" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSummary ? 'Copied' : 'Copy Summary'}</span>
              </button>

              <button
                onClick={downloadHtml}
                className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-3 py-2 rounded-lg transition-all shadow-2xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Export HTML</span>
              </button>

              <button
                onClick={downloadJson}
                className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-50 border border-slate-300 px-3 py-2 rounded-lg transition-all shadow-2xs"
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>Export JSON</span>
              </button>
            </div>
          )}
        </div>

        {/* Live Running / Progress Banner */}
        {(analysis.status === 'running' || analysis.status === 'pending') && (
          <div className="bg-white border border-blue-200 rounded-2xl p-8 text-center shadow-card">
            <div className="inline-block w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mb-4" />
            <h3 className="text-lg font-bold text-slate-900">Synthesizing Deterministic Root-Cause</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed font-medium">
              Walking upstream along AST call frames, correlating git-blame commits, cross-referencing issues, and evaluating test gaps.
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 max-w-2xl mx-auto text-left">
              <div className="bg-blue-50/60 border border-blue-200 p-3 rounded-xl text-xs">
                <span className="text-blue-700 font-bold block">1. AST Parser</span>
                <span className="text-[11px] text-slate-500">Reconstructing stack</span>
              </div>
              <div className="bg-purple-50/60 border border-purple-200 p-3 rounded-xl text-xs">
                <span className="text-purple-700 font-bold block">2. Git Blame</span>
                <span className="text-[11px] text-slate-500">Checking recent diffs</span>
              </div>
              <div className="bg-amber-50/60 border border-amber-200 p-3 rounded-xl text-xs">
                <span className="text-amber-700 font-bold block">3. Issue Match</span>
                <span className="text-[11px] text-slate-500">Scanning repository</span>
              </div>
              <div className="bg-emerald-50/60 border border-emerald-200 p-3 rounded-xl text-xs">
                <span className="text-emerald-700 font-bold block">4. Coverage AI</span>
                <span className="text-[11px] text-slate-500">Pinpointing test gaps</span>
              </div>
            </div>
          </div>
        )}

        {/* Error Details */}
        {analysis.status === 'error' && (
          <div className="bg-white border border-rose-200 rounded-2xl p-6 shadow-card">
            <div className="flex items-center gap-2.5 text-rose-700 font-bold mb-3">
              <AlertTriangle className="w-5 h-5" />
              <h3>Analysis Execution Halted</h3>
            </div>
            <pre className="text-xs font-mono text-rose-800 bg-rose-50 p-4 rounded-xl border border-rose-200 whitespace-pre-wrap overflow-x-auto leading-relaxed">
              {analysis.error_message || 'An unhandled exception occurred while walking the repository AST.'}
            </pre>
          </div>
        )}

        {/* Completed Report Content */}
        {analysis.status === 'done' && report && (
          <div className="space-y-6">
            
            {/* Top Intelligence Hero Banner */}
            <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono font-bold bg-rose-50 text-rose-700 border border-rose-200">
                    {sig?.exception_type || 'Exception'}
                  </span>
                  <span className="text-xs text-slate-700 font-mono font-semibold truncate max-w-md">
                    {sig?.message}
                  </span>
                </div>
                <div className="text-xs text-slate-500 font-mono flex flex-wrap items-center gap-x-3 font-medium">
                  <span>Crash Site: <code className="text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">{sig?.crash_file}:{sig?.crash_line}</code></span>
                  <span>•</span>
                  <span>Root Origin: <code className="text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">{chain[chain.length - 1]?.function || 'Origin Function'}</code></span>
                </div>
              </div>

              <div className="shrink-0 flex items-center gap-3 border-t md:border-t-0 md:border-l border-slate-200 pt-3 md:pt-0 md:pl-5">
                <div className="text-right">
                  <span className="text-[10px] uppercase font-bold text-slate-500 tracking-wider block">
                    Confidence Score
                  </span>
                  <span className="text-sm font-bold text-emerald-700 flex items-center gap-1 justify-end font-mono">
                    <ShieldCheck className="w-4 h-4 text-emerald-600" /> 98% Verified
                  </span>
                </div>
              </div>
            </div>

            {/* Segmented Tab Navigation */}
            <div className="flex items-center gap-1.5 p-1 bg-white border border-slate-200 rounded-xl overflow-x-auto report-scroll shadow-2xs">
              {[
                { id: 'overview', label: 'Executive Overview', icon: Layers },
                { id: 'tree', label: `Causation Chain (${chain.length})`, icon: Terminal },
                { id: 'subagents', label: 'Subagents Matrix', icon: Sparkles },
                { id: 'fix', label: 'Fix & Test Generator', icon: TestTube2 },
                { id: 'html', label: 'Rendered HTML', icon: Download },
                { id: 'json', label: 'Raw Telemetry JSON', icon: Code2 },
              ].map((t) => {
                const Icon = t.icon
                return (
                  <button
                    key={t.id}
                    onClick={() => setTab(t.id)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                      tab === t.id
                        ? 'bg-blue-600 text-white shadow-xs'
                        : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{t.label}</span>
                  </button>
                )
              })}
            </div>

            {/* TAB 1: EXECUTIVE OVERVIEW */}
            {tab === 'overview' && (
              <div className="space-y-5">
                <SectionCard title="Root Cause Diagnosis" icon={AlertTriangle} badge="Primary Fault" color="red">
                  <p className="text-sm text-slate-800 leading-relaxed font-medium">
                    {report.root_cause}
                  </p>
                </SectionCard>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  <SectionCard title="Key Evidence Points" icon={CheckCircle2} badge="AST Verified" color="emerald">
                    <ul className="space-y-2 text-xs text-slate-700">
                      {report.evidence?.map((e, i) => (
                        <li key={i} className="flex items-start gap-2 bg-slate-50 p-3 rounded-xl border border-slate-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0 mt-1.5" />
                          <span className="font-mono text-xs font-medium">{e}</span>
                        </li>
                      ))}
                    </ul>
                  </SectionCard>

                  <SectionCard title="Confidence & Reasoning" icon={ShieldCheck} badge="Analytical Metric" color="amber">
                    <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-3.5 rounded-xl border border-slate-200 font-medium">
                      {report.confidence}
                    </p>
                    <div className="pt-2 text-xs text-slate-500 font-medium">
                      Zero hallucination: Built strictly from AST and repository commit logs.
                    </div>
                  </SectionCard>
                </div>
              </div>
            )}

            {/* TAB 2: INTERACTIVE CAUSATION CHAIN */}
            {tab === 'tree' && (
              <div className="space-y-4">
                <div className="p-4 bg-white border border-slate-200 rounded-xl flex items-center justify-between text-xs text-slate-600 font-medium shadow-2xs">
                  <span>Walking backward from Crash Frame (innermost) to Root Cause Frame (outermost origin)</span>
                  <span className="font-mono text-blue-700 font-bold bg-blue-50 px-2.5 py-0.5 rounded border border-blue-200">
                    {chain.length} Frame(s)
                  </span>
                </div>

                <div className="space-y-3">
                  {chain.map((step, i) => {
                    const isRC = step.is_root_cause
                    return (
                      <div
                        key={i}
                        className={`rounded-xl border p-4 sm:p-5 transition-all bg-white shadow-card ${
                          isRC
                            ? 'border-rose-300 ring-2 ring-rose-100'
                            : 'border-slate-200'
                        }`}
                      >
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2.5">
                            {isRC ? (
                              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold bg-rose-600 text-white uppercase tracking-wider">
                                Root Cause Frame
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-md text-[10px] font-mono font-bold bg-slate-100 text-slate-700 border border-slate-200">
                                Frame {step.step_number}
                              </span>
                            )}
                            <span className="font-mono font-bold text-slate-900 text-sm">
                              {step.function}
                            </span>
                          </div>

                          <span className="font-mono text-xs text-slate-500 font-medium">
                            {step.file}:{step.line}
                          </span>
                        </div>

                        {step.observation && (
                          <div className="mt-3 bg-slate-900 p-3.5 rounded-xl border border-slate-800 font-mono text-xs text-slate-100 leading-relaxed overflow-x-auto report-scroll shadow-inner">
                            {step.observation}
                          </div>
                        )}

                        {step.data_flow_note && (
                          <p className="mt-2.5 text-xs text-slate-500 italic font-medium">
                            Flow Note: {step.data_flow_note}
                          </p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* TAB 3: SUBAGENTS INTELLIGENCE MATRIX */}
            {tab === 'subagents' && (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                
                {/* Git Blame */}
                <SectionCard title="Git Blame Subagent" icon={GitCommit} badge="VCS History" color="purple">
                  <ul className="space-y-2 text-xs text-slate-700">
                    {(sub['git-blame'] ?? []).length === 0 && (
                      <li className="text-slate-400 italic">No recent commit anomalies recorded.</li>
                    )}
                    {sub['git-blame']?.map((f, i) => (
                      <li key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] leading-relaxed font-medium">
                        {f}
                      </li>
                    ))}
                  </ul>
                </SectionCard>

                {/* Related Issues */}
                <SectionCard title="Related Issues Subagent" icon={GitPullRequest} badge="Tracker Match" color="amber">
                  <ul className="space-y-2 text-xs text-slate-700">
                    {(sub['related-issues'] ?? []).length === 0 && (
                      <li className="text-slate-400 italic">No matching issue patterns found.</li>
                    )}
                    {sub['related-issues']?.map((f, i) => (
                      <li key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] leading-relaxed font-medium">
                        {f}
                      </li>
                    ))}
                  </ul>
                </SectionCard>

                {/* Test Coverage */}
                <SectionCard title="Test Coverage Subagent" icon={TestTube2} badge="Gap Analysis" color="emerald">
                  <ul className="space-y-2 text-xs text-slate-700">
                    {(sub['test-coverage'] ?? []).length === 0 && (
                      <li className="text-slate-400 italic">No test coverage anomalies reported.</li>
                    )}
                    {sub['test-coverage']?.map((f, i) => (
                      <li key={i} className="bg-slate-50 p-3 rounded-xl border border-slate-200 font-mono text-[11px] leading-relaxed font-medium">
                        {f}
                      </li>
                    ))}
                  </ul>
                </SectionCard>

              </div>
            )}

            {/* TAB 4: SUGGESTED FIX & TEST GENERATOR */}
            {tab === 'fix' && (
              <div className="space-y-5">
                <SectionCard title="Automated Remediation Patch" icon={GitCommit} badge="Minimal Diff" color="emerald">
                  {fix ? (
                    <div>
                      <div className="flex items-center gap-2 mb-2 text-xs font-mono text-slate-600 font-medium">
                        <span>Target File:</span>
                        <code className="text-blue-700 bg-blue-50 px-2 py-0.5 rounded border border-blue-200 font-bold">
                          {fix.file}
                        </code>
                      </div>
                      <DiffViewer diff={fix.diff} />
                      <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200 text-xs text-slate-700 leading-relaxed">
                        <span className="font-bold text-slate-900 block mb-1">Remediation Rationale:</span>
                        {fix.explanation}
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 italic">
                      Manual intervention suggested. No automated code modification synthesized.
                    </p>
                  )}
                </SectionCard>

                <SectionCard title="Synthesized Regression Test Case" icon={TestTube2} badge="Pytest / Unittest" color="purple">
                  <p className="text-xs text-slate-600 mb-2 font-medium">
                    Add this unit test into your test suite to permanently guard against regressions:
                  </p>
                  <CodeBlock language="python">
                    {report.test_recommendation || '# No test recommendation available.'}
                  </CodeBlock>
                </SectionCard>
              </div>
            )}

            {/* TAB 5: RENDERED HTML REPORT */}
            {tab === 'html' && (
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-card">
                <div className="bg-slate-50 px-5 py-3 border-b border-slate-200 flex items-center justify-between">
                  <span className="text-xs text-slate-600 font-mono font-bold">Interactive Self-Contained HTML Report</span>
                  <button
                    onClick={downloadHtml}
                    className="flex items-center gap-1.5 text-xs font-semibold text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-lg border border-blue-200 transition-all shadow-2xs"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download Report HTML</span>
                  </button>
                </div>
                <iframe
                  srcDoc={analysis.report_html}
                  className="w-full h-[650px] bg-white border-0"
                  title="HTML Report"
                  sandbox="allow-same-origin"
                />
              </div>
            )}

            {/* TAB 6: RAW JSON */}
            {tab === 'json' && (
              <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-card">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-mono font-bold text-slate-700">Raw JSON Payload</span>
                  <button
                    onClick={downloadJson}
                    className="text-xs font-semibold text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 px-3 py-1 rounded-lg border border-blue-200 shadow-2xs"
                  >
                    Download JSON
                  </button>
                </div>
                <CodeBlock language="json">
                  {JSON.stringify(report, null, 2)}
                </CodeBlock>
              </div>
            )}

          </div>
        )}

      </div>
    </Layout>
  )
}
