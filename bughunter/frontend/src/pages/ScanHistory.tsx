import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { listScans, stopScan, getPrograms } from '../lib/api'
import { useScanLogs } from '../lib/websocket'
import ScanLogViewer from '../components/ui/ScanLogViewer'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/ui/EmptyState'
import { History, Square } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export default function ScanHistory() {
  const [programId, setProgramId] = useState('')
  const [page, setPage] = useState(0)
  const [logScan, setLogScan] = useState<string | null>(null)
  const { logs } = useScanLogs(logScan)
  const limit = 50
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data, refetch } = useQuery({ queryKey: ['scan-history', programId, page], queryFn: () => listScans({ program_id: programId || undefined, limit, offset: page * limit }), refetchInterval: 10000 })
  const stop = useMutation({ mutationFn: stopScan, onSuccess: () => { toast.success('Stop signal sent'); refetch() } })
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3">
        <select className="input w-48" value={programId} onChange={e => { setProgramId(e.target.value); setPage(0) }}>
          <option value="">All programs</option>
          {(programs?.data ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <span className="text-gray-500 text-sm self-center">{total} total</span>
      </div>

      {logScan && (
        <div className="card">
          <div className="flex justify-between mb-2"><span className="text-sm text-gray-300">Scan Logs</span><button onClick={() => setLogScan(null)} className="text-xs text-gray-500">Close</button></div>
          <ScanLogViewer logs={logs} />
        </div>
      )}

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-dark-600"><tr>
            <th className="table-header">Type</th><th className="table-header">Status</th>
            <th className="table-header">Progress</th><th className="table-header">Started</th>
            <th className="table-header">Duration</th><th className="table-header">Actions</th>
          </tr></thead>
          <tbody>
            {items.map((s: any) => {
              const dur = s.started_at && s.finished_at ? Math.round((new Date(s.finished_at).getTime() - new Date(s.started_at).getTime()) / 1000) + 's' : '—'
              return (
                <tr key={s.id} className="table-row">
                  <td className="table-cell font-mono text-xs">{s.type}</td>
                  <td className="table-cell"><StatusBadge value={s.status} /></td>
                  <td className="table-cell">
                    <div className="flex items-center gap-2">
                      <div className="bg-dark-700 rounded-full h-1.5 w-20"><div className="bg-accent-500 h-1.5 rounded-full" style={{ width: `${s.progress}%` }} /></div>
                      <span className="text-xs text-gray-500">{s.progress}%</span>
                    </div>
                  </td>
                  <td className="table-cell text-xs text-gray-500">{s.started_at ? formatDistanceToNow(new Date(s.started_at), { addSuffix: true }) : '—'}</td>
                  <td className="table-cell text-xs text-gray-500">{dur}</td>
                  <td className="table-cell">
                    <div className="flex gap-2">
                      <button onClick={() => setLogScan(s.id)} className="text-xs text-accent-500 hover:underline">Logs</button>
                      {s.status === 'running' && <button onClick={() => stop.mutate(s.id)} className="text-xs text-danger-400 flex items-center gap-1"><Square size={10} />Stop</button>}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {items.length === 0 && <EmptyState icon={<History size={40} />} title="No scans yet" description="Start a scan from Reconnaissance page" />}
      </div>
      <div className="flex gap-2">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary disabled:opacity-40">← Prev</button>
        <span className="text-gray-500 text-sm self-center">Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}</span>
        <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="btn-secondary disabled:opacity-40">Next →</button>
      </div>
    </div>
  )
}

