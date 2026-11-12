import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getLiveHosts } from '../lib/api'
import EmptyState from '../components/ui/EmptyState'
import { Server } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function LiveHosts() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50
  const { data, isLoading } = useQuery({ queryKey: ['live-hosts', q, page], queryFn: () => getLiveHosts({ q: q || undefined, limit, offset: page * limit }), refetchInterval: 30000 })
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0
  const statusColor = (c: number) => c < 300 ? 'text-green-400' : c < 400 ? 'text-blue-400' : c < 500 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3">
        <input className="input w-72" placeholder="Search URL..." value={q} onChange={e => { setQ(e.target.value); setPage(0) }} />
        <span className="text-gray-500 text-sm self-center">{total} total</span>
      </div>
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-dark-600"><tr>
            <th className="table-header">URL</th><th className="table-header">Status</th>
            <th className="table-header">Title</th><th className="table-header">Technologies</th>
            <th className="table-header">Last Probed</th>
          </tr></thead>
          <tbody>
            {items.map((h: any) => (
              <tr key={h.id} className="table-row">
                <td className="table-cell font-mono text-xs max-w-xs truncate"><a href={h.url} target="_blank" rel="noreferrer" className="text-accent-500 hover:underline">{h.url}</a></td>
                <td className="table-cell"><span className={`font-mono font-bold text-sm ${statusColor(h.status_code)}`}>{h.status_code}</span></td>
                <td className="table-cell text-gray-300 text-xs max-w-[200px] truncate">{h.title || '—'}</td>
                <td className="table-cell">{(h.tech ?? []).slice(0, 4).map((t: string) => <span key={t} className="text-xs bg-dark-700 px-1.5 py-0.5 rounded mr-1">{t}</span>)}</td>
                <td className="table-cell text-gray-500 text-xs">{formatDistanceToNow(new Date(h.last_probed), { addSuffix: true })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && items.length === 0 && <EmptyState icon={<Server size={40} />} title="No live hosts yet" description="Run a probe scan to identify live services" />}
      </div>
      <div className="flex gap-2">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary disabled:opacity-40">← Prev</button>
        <span className="text-gray-500 text-sm self-center">Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}</span>
        <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="btn-secondary disabled:opacity-40">Next →</button>
      </div>
    </div>
  )
}

