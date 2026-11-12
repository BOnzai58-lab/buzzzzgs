const statusColors: Record<string, string> = {
  queued: 'bg-gray-800 text-gray-400',
  running: 'bg-blue-900/40 text-blue-400 animate-pulse',
  done: 'bg-green-900/40 text-green-400',
  failed: 'bg-red-900/40 text-red-400',
  stopped: 'bg-orange-900/40 text-orange-400',
  potential: 'bg-yellow-900/40 text-yellow-400',
  verified: 'bg-green-900/40 text-green-400',
  false_positive: 'bg-gray-800 text-gray-500',
  informational: 'bg-gray-800 text-gray-400',
  needs_manual_verification: 'bg-purple-900/40 text-purple-400',
  out_of_scope: 'bg-gray-900 text-gray-600',
  draft: 'bg-yellow-900/40 text-yellow-400',
  ready: 'bg-green-900/40 text-green-400',
  pending: 'bg-orange-900/40 text-orange-400',
  approved: 'bg-green-900/40 text-green-400',
  rejected: 'bg-red-900/40 text-red-400',
}
export default function StatusBadge({ value }: { value: string }) {
  const cls = statusColors[value] || 'bg-gray-800 text-gray-400'
  return <span className={`text-xs px-2 py-0.5 rounded font-medium ${cls}`}>{value?.replace(/_/g, ' ')}</span>
}

