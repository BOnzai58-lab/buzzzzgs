import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAssets, getPrograms } from '../lib/api'
import EmptyState from '../components/ui/EmptyState'
import { Globe } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Assets() {
  const [programId, setProgramId] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data, isLoading } = useQuery({
    queryKey: ['assets', programId, q, page],
    queryFn: () => getAssets({ program_id: programId || undefined, q: q || undefined, limit, offset: page * limit }),
    refetchInterval: 30000,
  })
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0
  const statusColor: Record<string, string> = { in_scope: 'text-green-400', out_of_scope: 'text-red-400', unknown: 'text-gray-500' }

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3 flex-wrap">
        <select className="input w-48" value={programId} onChange={e => { setProgramId(e.target.value); setPage(0) }}>
          <option value="">All programs</option>
          {(programs?.data ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input className="input w-64" placeholder="Search domain..." value={q} onChange={e => { setQ(e.target.value); setPage(0) }} />
        <span className="text-gray-500 text-sm self-center">{total} total</span>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-dark-600"><tr>
            <th className="table-header">Domain</th><th className="table-header">Source</th>
            <th className="table-header">Scope</th><th className="table-header">HTTP</th>
            <th className="table-header">Technologies</th><th className="table-header">Last Seen</th>
          </tr></thead>
          <tbody>
            {items.map((a: any) => (
              <tr key={a.id} className="table-row">
                <td className="table-cell font-mono text-xs text-white">{a.domain}</td>
                <td className="table-cell"><span className="text-xs text-gray-500">{a.source}</span></td>
                <td className="table-cell"><span className={`text-xs font-medium ${statusColor[a.scope_status]}`}>{a.scope_status}</span></td>
                <td className="table-cell">{a.http_status ? <span className="text-xs font-mono">{a.http_status}</span> : '—'}</td>
                <td className="table-cell">{(a.technologies ?? []).slice(0, 3).map((t: string) => <span key={t} className="text-xs bg-dark-700 px-1.5 py-0.5 rounded mr-1">{t}</span>)}</td>
                <td className="table-cell text-gray-500 text-xs">{formatDistanceToNow(new Date(a.last_seen), { addSuffix: true })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && items.length === 0 && <EmptyState icon={<Globe size={40} />} title="No assets discovered yet" description="Run a subdomains scan to get started" />}
      </div>

      <div className="flex gap-2">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary disabled:opacity-40">← Prev</button>
        <span className="text-gray-500 text-sm self-center">Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}</span>
        <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="btn-secondary disabled:opacity-40">Next →</button>
      </div>
    </div>
  )
}

