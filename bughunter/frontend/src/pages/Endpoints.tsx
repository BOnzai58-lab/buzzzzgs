import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getEndpoints } from '../lib/api'
import EmptyState from '../components/ui/EmptyState'
import { Link2 } from 'lucide-react'

const methodColor: Record<string, string> = { GET: 'text-green-400', POST: 'text-blue-400', PUT: 'text-yellow-400', DELETE: 'text-red-400', PATCH: 'text-purple-400' }
const tagColor: Record<string, string> = { auth: 'bg-red-900/40 text-red-400', api: 'bg-blue-900/40 text-blue-400', admin: 'bg-orange-900/40 text-orange-400', upload: 'bg-purple-900/40 text-purple-400', history: 'bg-gray-800 text-gray-500' }

export default function Endpoints() {
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const limit = 50
  const { data, isLoading } = useQuery({ queryKey: ['endpoints', q, page], queryFn: () => getEndpoints({ q: q || undefined, limit, offset: page * limit }) })
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3">
        <input className="input w-72" placeholder="Search URL or param..." value={q} onChange={e => { setQ(e.target.value); setPage(0) }} />
        <span className="text-gray-500 text-sm self-center">{total} total</span>
      </div>
      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-dark-600"><tr>
            <th className="table-header">Method</th><th className="table-header">URL</th>
            <th className="table-header">Tags</th><th className="table-header">AI Rank</th><th className="table-header">Source</th>
          </tr></thead>
          <tbody>
            {items.map((e: any) => (
              <tr key={e.id} className="table-row">
                <td className="table-cell"><span className={`font-mono text-xs font-bold ${methodColor[e.method] || 'text-gray-400'}`}>{e.method}</span></td>
                <td className="table-cell font-mono text-xs text-gray-300 max-w-xs truncate">{e.url}</td>
                <td className="table-cell">{(e.tags ?? []).map((t: string) => <span key={t} className={`text-xs px-1.5 py-0.5 rounded mr-1 ${tagColor[t] || 'bg-dark-700 text-gray-400'}`}>{t}</span>)}</td>
                <td className="table-cell">{e.ai_rank != null ? <span className="text-accent-500 font-mono text-xs">{(e.ai_rank * 100).toFixed(0)}%</span> : '—'}</td>
                <td className="table-cell text-xs text-gray-500">{e.source}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && items.length === 0 && <EmptyState icon={<Link2 size={40} />} title="No endpoints discovered yet" description="Run a crawl or history scan" />}
      </div>
      <div className="flex gap-2">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary disabled:opacity-40">← Prev</button>
        <span className="text-gray-500 text-sm self-center">Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}</span>
        <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="btn-secondary disabled:opacity-40">Next →</button>
      </div>
    </div>
  )
}

