import { useQuery } from '@tanstack/react-query'
import { Bug, Globe, Server, Link2, Target, ShieldCheck, XCircle, Clock } from 'lucide-react'
import { getOverviewStats, getFindings, listScans } from '../lib/api'
import StatCard from '../components/ui/StatCard'
import SeverityChart from '../components/ui/SeverityChart'
import Badge from '../components/ui/Badge'
import StatusBadge from '../components/ui/StatusBadge'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { formatDistanceToNow } from 'date-fns'

export default function Overview() {
  const { data: stats, isLoading } = useQuery({ queryKey: ['stats'], queryFn: () => getOverviewStats(), refetchInterval: 30000 })
  const { data: findings } = useQuery({ queryKey: ['findings-recent'], queryFn: () => getFindings({ limit: 5 }) })
  const { data: scans } = useQuery({ queryKey: ['scans-recent'], queryFn: () => listScans({ limit: 5 }) })

  const s = stats?.data
  if (isLoading) return <div className="flex items-center justify-center h-64"><LoadingSpinner /></div>

  return (
    <div className="p-6 space-y-6">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<Target size={20} />} label="Programs" value={s?.total_programs ?? 0} />
        <StatCard icon={<Globe size={20} />} label="Subdomains" value={s?.total_subdomains ?? 0} />
        <StatCard icon={<Server size={20} />} label="Live Hosts" value={s?.live_hosts ?? 0} />
        <StatCard icon={<Link2 size={20} />} label="Endpoints" value={s?.endpoints ?? 0} />
        <StatCard icon={<Bug size={20} />} label="Potential Vulns" value={s?.potential_vulnerabilities ?? 0} color="text-warn-500" />
        <StatCard icon={<ShieldCheck size={20} />} label="Verified" value={s?.verified_vulnerabilities ?? 0} color="text-success-500" />
        <StatCard icon={<XCircle size={20} />} label="False Positives" value={s?.false_positives ?? 0} color="text-gray-500" />
        <StatCard icon={<Clock size={20} />} label="Pending Approvals" value={s?.pending_approvals ?? 0} color="text-warn-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Severity Chart */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Severity Distribution</h2>
          <SeverityChart data={s?.severity_distribution ?? {}} />
        </div>

        {/* Recent Scans */}
        <div className="card">
          <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Scans</h2>
          <div className="space-y-2">
            {(scans?.data?.items ?? []).length === 0 && <p className="text-gray-600 text-sm">No scans yet</p>}
            {(scans?.data?.items ?? []).map((scan: any) => (
              <div key={scan.id} className="flex items-center justify-between py-2 border-b border-dark-600 last:border-0">
                <div>
                  <span className="text-xs font-mono text-gray-400">{scan.type}</span>
                  <div className="mt-0.5">
                    <div className="bg-dark-700 rounded-full h-1 w-32">
                      <div className="bg-accent-500 h-1 rounded-full" style={{ width: `${scan.progress}%` }} />
                    </div>
                  </div>
                </div>
                <StatusBadge value={scan.status} />
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Findings */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Findings</h2>
        {(findings?.data?.items ?? []).length === 0
          ? <p className="text-gray-600 text-sm">No findings yet</p>
          : <table className="w-full"><thead><tr>
              <th className="table-header">Name</th><th className="table-header">Severity</th>
              <th className="table-header">Status</th><th className="table-header">Found</th>
            </tr></thead><tbody>
              {(findings?.data?.items ?? []).map((f: any) => (
                <tr key={f.id} className="table-row">
                  <td className="table-cell font-medium text-white">{f.name}</td>
                  <td className="table-cell"><Badge value={f.severity} /></td>
                  <td className="table-cell"><StatusBadge value={f.status} /></td>
                  <td className="table-cell text-gray-500">{formatDistanceToNow(new Date(f.created_at), { addSuffix: true })}</td>
                </tr>
              ))}
          </tbody></table>}
      </div>
    </div>
  )
}

