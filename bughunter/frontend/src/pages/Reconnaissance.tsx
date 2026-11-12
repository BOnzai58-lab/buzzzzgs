import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Play, Square } from 'lucide-react'
import { getPrograms, createScan, listScans, stopScan } from '../lib/api'
import { useScanLogs } from '../lib/websocket'
import ScanLogViewer from '../components/ui/ScanLogViewer'
import StatusBadge from '../components/ui/StatusBadge'
import toast from 'react-hot-toast'

export default function Reconnaissance() {
  const [programId, setProgramId] = useState('')
  const [scanType, setScanType] = useState('subdomains')
  const [targets, setTargets] = useState('')
  const [activeScanId, setActiveScanId] = useState<string | null>(null)
  const { logs } = useScanLogs(activeScanId)

  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data: scans, refetch } = useQuery({ queryKey: ['scans', programId], queryFn: () => listScans({ program_id: programId || undefined, limit: 10 }), refetchInterval: 5000 })

  const start = useMutation({
    mutationFn: () => createScan(programId, { type: scanType, targets: targets.split('\n').map(s => s.trim()).filter(Boolean) }),
    onSuccess: res => { toast.success('Scan started'); setActiveScanId(res.data.id); refetch() },
    onError: (e: any) => toast.error(e.response?.data?.detail || 'Failed to start scan'),
  })
  const stop = useMutation({ mutationFn: stopScan, onSuccess: () => { toast.success('Stop signal sent'); refetch() } })

  return (
    <div className="p-6 space-y-6">
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Launch Scan</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div>
            <label className="label">Program</label>
            <select className="input" value={programId} onChange={e => setProgramId(e.target.value)}>
              <option value="">Select program...</option>
              {(programs?.data ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Scan Type</label>
            <select className="input" value={scanType} onChange={e => setScanType(e.target.value)}>
              {['subdomains', 'resolve', 'probe', 'crawl', 'history', 'vuln'].map(t => <option key={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="label">Targets (optional, one per line)</label>
            <textarea className="input h-20 resize-none" value={targets} onChange={e => setTargets(e.target.value)} placeholder="Leave empty to use all in-scope assets" />
          </div>
        </div>
        <button onClick={() => start.mutate()} disabled={!programId || start.isPending} className="btn-primary flex items-center gap-2 disabled:opacity-50">
          <Play size={14} />Start Scan
        </button>
      </div>

      {/* Active Scan Logs */}
      {activeScanId && (
        <div className="card">
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-gray-300">Live Scan Logs</h2>
            <button onClick={() => setActiveScanId(null)} className="text-xs text-gray-500 hover:text-gray-300">Detach</button>
          </div>
          <ScanLogViewer logs={logs} />
        </div>
      )}

      {/* Scan list */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Recent Scans</h2>
        <table className="w-full">
          <thead><tr>
            <th className="table-header">Type</th><th className="table-header">Status</th>
            <th className="table-header">Progress</th><th className="table-header">Started</th>
            <th className="table-header">Actions</th>
          </tr></thead>
          <tbody>
            {(scans?.data?.items ?? []).map((s: any) => (
              <tr key={s.id} className="table-row">
                <td className="table-cell font-mono text-xs">{s.type}</td>
                <td className="table-cell"><StatusBadge value={s.status} /></td>
                <td className="table-cell">
                  <div className="flex items-center gap-2">
                    <div className="bg-dark-700 rounded-full h-1.5 w-24">
                      <div className="bg-accent-500 h-1.5 rounded-full transition-all" style={{ width: `${s.progress}%` }} />
                    </div>
                    <span className="text-xs text-gray-500">{s.progress}%</span>
                  </div>
                </td>
                <td className="table-cell text-gray-500 text-xs">{s.started_at ? new Date(s.started_at).toLocaleString() : '—'}</td>
                <td className="table-cell">
                  <div className="flex gap-2">
                    <button onClick={() => setActiveScanId(s.id)} className="text-xs text-accent-500 hover:underline">Logs</button>
                    {s.status === 'running' && <button onClick={() => stop.mutate(s.id)} className="text-xs text-danger-400 flex items-center gap-1"><Square size={10} />Stop</button>}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

