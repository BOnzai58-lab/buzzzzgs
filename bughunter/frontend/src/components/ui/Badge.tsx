const sevColors: Record<string, string> = {
  critical: 'bg-red-900/40 text-red-400 border-red-700/50',
  high: 'bg-orange-900/40 text-orange-400 border-orange-700/50',
  medium: 'bg-yellow-900/40 text-yellow-400 border-yellow-700/50',
  low: 'bg-blue-900/40 text-blue-400 border-blue-700/50',
  info: 'bg-gray-800 text-gray-400 border-gray-700',
}
export default function Badge({ value }: { value: string }) {
  const cls = sevColors[value?.toLowerCase()] || sevColors.info
  return <span className={`text-xs px-2 py-0.5 rounded border font-medium uppercase ${cls}`}>{value}</span>
}

