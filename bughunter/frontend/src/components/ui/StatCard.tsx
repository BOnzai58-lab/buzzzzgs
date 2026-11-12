interface Props { icon: React.ReactNode; label: string; value: number | string; sub?: string; color?: string }
export default function StatCard({ icon, label, value, sub, color = 'text-accent-500' }: Props) {
  return (
    <div className="card flex items-center gap-4">
      <div className={`${color} bg-current/10 p-3 rounded-lg shrink-0`}>{icon}</div>
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
        {sub && <p className="text-xs text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

