import { Clock, Activity, CheckCircle2, AlertTriangle } from 'lucide-react'

const configs = {
  pending: {
    bg: 'bg-amber-50 text-amber-700 border-amber-200',
    dot: 'bg-amber-500',
    icon: Clock,
    label: 'Pending',
  },
  running: {
    bg: 'bg-blue-50 text-blue-700 border-blue-200 animate-pulse',
    dot: 'bg-blue-500',
    icon: Activity,
    label: 'Tracing...',
  },
  done: {
    bg: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    dot: 'bg-emerald-500',
    icon: CheckCircle2,
    label: 'Completed',
  },
  error: {
    bg: 'bg-rose-50 text-rose-700 border-rose-200',
    dot: 'bg-rose-500',
    icon: AlertTriangle,
    label: 'Failed',
  },
}

export default function StatusBadge({ status }) {
  const cfg = configs[status] ?? {
    bg: 'bg-slate-100 text-slate-700 border-slate-200',
    dot: 'bg-slate-400',
    icon: Clock,
    label: status,
  }
  const Icon = cfg.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold border ${cfg.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      <span className="capitalize">{cfg.label}</span>
    </span>
  )
}
