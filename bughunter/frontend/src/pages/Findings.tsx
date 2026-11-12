import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getFindings, getPrograms, getFinding, analyzeFinding, updateFindingStatus, requestVerification, generateReport } from '../lib/api'
import Badge from '../components/ui/Badge'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/ui/EmptyState'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { Bug, X, Brain, ShieldCheck, FileText } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

function FindingModal({ findingId, onClose }: { findingId: string; onClose: () => void }) {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['finding', findingId], queryFn: () => getFinding(findingId) })
  const [statusForm, setStatusForm] = useState({ status: '', note: '' })
  const analyze = useMutation({ mutationFn: () => analyzeFinding(findingId), onSuccess: () => toast.success('AI analysis queued') })
  const changeStatus = useMutation({ mutationFn: () => updateFindingStatus(findingId, { status: statusForm.status, note: statusForm.note }), onSuccess: () => { qc.invalidateQueries({ queryKey: ['finding', findingId] }); toast.success('Status updated') } })
  const verify = useMutation({ mutationFn: () => requestVerification(findingId), onSuccess: () => toast.success('Verification requested — awaiting approval') })
  const report = useMutation({ mutationFn: () => generateReport(findingId), onSuccess: () => toast.success('Report generation queued') })

  const f = data?.data?.finding
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
      <div className="card max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        <div className="flex items-start justify-between mb-4">
          <h3 className="text-white font-semibold">{f?.name || '...'}</h3>
          <button onClick={onClose}><X size={18} className="text-gray-500 hover:text-white" /></button>
        </div>
        {isLoading ? <LoadingSpinner /> : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><p className="label">Severity</p><Badge value={f?.severity} /></div>
              <div><p className="label">Status</p><StatusBadge value={f?.status} /></div>
              <div><p className="label">Scanner</p><span className="text-gray-300 font-mono text-xs">{f?.scanner}</span></div>
              <div><p className="label">Category</p><span className="text-gray-300 text-xs">{f?.category}</span></div>
            </div>

            {/* Evidence */}
            <div><p className="label mb-2">Evidence ({data?.data?.evidence?.length ?? 0})</p>
              <div className="space-y-1">
                {(data?.data?.evidence ?? []).map((e: any) => (
                  <div key={e.id} className="bg-dark-900 rounded p-2 text-xs font-mono text-gray-400 flex gap-2">
                    <span className="text-accent-500">[{e.kind}]</span><span>{e.content_ref}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Validation history */}
            <div><p className="label mb-2">Validation History</p>
              <div className="space-y-1">
                {(data?.data?.validation_history ?? []).map((h: any, i: number) => (
                  <div key={i} className="text-xs text-gray-500 flex gap-2">
                    <span className="text-gray-600">{new Date(h.at).toLocaleString()}</span>
                    <span>{h.from} → <span className="text-white">{h.to}</span></span>
                    <span>by {h.actor.substring(0, 8)}…</span>
                    {h.reason && <span className="text-gray-600">({h.reason})</span>}
                  </div>
                ))}
              </div>
            </div>

            {/* Change Status */}
            <div className="border-t border-dark-600 pt-4">
              <p className="label mb-2">Change Status</p>
              <div className="flex gap-2">
                <select className="input w-48" value={statusForm.status} onChange={e => setStatusForm(p => ({ ...p, status: e.target.value }))}>
                  <option value="">Select status...</option>
                  {['informational', 'potential', 'needs_manual_verification', 'false_positive', 'out_of_scope'].map(s => <option key={s}>{s}</option>)}
                </select>
                <input className="input flex-1" placeholder="Note (optional)" value={statusForm.note} onChange={e => setStatusForm(p => ({ ...p, note: e.target.value }))} />
                <button onClick={() => changeStatus.mutate()} disabled={!statusForm.status} className="btn-secondary disabled:opacity-40">Update</button>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-2 flex-wrap pt-2">
              <button onClick={() => analyze.mutate()} className="btn-secondary flex items-center gap-1 text-xs"><Brain size={13} />AI Analysis</button>
              <button onClick={() => verify.mutate()} className="btn-secondary flex items-center gap-1 text-xs"><ShieldCheck size={13} />Request Verification</button>
              <button onClick={() => report.mutate()} className="btn-secondary flex items-center gap-1 text-xs"><FileText size={13} />Generate Report</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function Findings() {
  const [programId, setProgramId] = useState('')
  const [severity, setSeverity] = useState('')
  const [status, setStatus] = useState('')
  const [q, setQ] = useState('')
  const [page, setPage] = useState(0)
  const [selected, setSelected] = useState<string | null>(null)
  const limit = 50
  const { data: programs } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const { data, isLoading } = useQuery({
    queryKey: ['findings', programId, severity, status, q, page],
    queryFn: () => getFindings({ program_id: programId || undefined, severity: severity || undefined, status: status || undefined, q: q || undefined, limit, offset: page * limit }),
    refetchInterval: 30000,
  })
  const items = data?.data?.items ?? []
  const total = data?.data?.total ?? 0

  return (
    <div className="p-6 space-y-4">
      <div className="flex gap-3 flex-wrap">
        <select className="input w-40" value={programId} onChange={e => { setProgramId(e.target.value); setPage(0) }}>
          <option value="">All programs</option>
          {(programs?.data ?? []).map((p: any) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select className="input w-32" value={severity} onChange={e => { setSeverity(e.target.value); setPage(0) }}>
          <option value="">All severities</option>
          {['critical', 'high', 'medium', 'low', 'info'].map(s => <option key={s}>{s}</option>)}
        </select>
        <select className="input w-40" value={status} onChange={e => { setStatus(e.target.value); setPage(0) }}>
          <option value="">All statuses</option>
          {['potential', 'informational', 'needs_manual_verification', 'verified', 'false_positive', 'out_of_scope'].map(s => <option key={s}>{s}</option>)}
        </select>
        <input className="input w-48" placeholder="Search..." value={q} onChange={e => { setQ(e.target.value); setPage(0) }} />
        <span className="text-gray-500 text-sm self-center">{total} total</span>
      </div>

      <div className="card p-0 overflow-hidden">
        <table className="w-full">
          <thead className="border-b border-dark-600"><tr>
            <th className="table-header">Name</th><th className="table-header">Severity</th>
            <th className="table-header">Category</th><th className="table-header">Status</th>
            <th className="table-header">Scanner</th><th className="table-header">Found</th>
          </tr></thead>
          <tbody>
            {items.map((f: any) => (
              <tr key={f.id} className="table-row cursor-pointer" onClick={() => setSelected(f.id)}>
                <td className="table-cell font-medium text-white hover:text-accent-500">{f.name}</td>
                <td className="table-cell"><Badge value={f.severity} /></td>
                <td className="table-cell text-xs text-gray-400">{f.category}</td>
                <td className="table-cell"><StatusBadge value={f.status} /></td>
                <td className="table-cell text-xs font-mono text-gray-500">{f.scanner}</td>
                <td className="table-cell text-gray-500 text-xs">{formatDistanceToNow(new Date(f.created_at), { addSuffix: true })}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && items.length === 0 && <EmptyState icon={<Bug size={40} />} title="No findings yet" description="Run a vulnerability scan to discover potential issues" />}
      </div>

      <div className="flex gap-2">
        <button disabled={page === 0} onClick={() => setPage(p => p - 1)} className="btn-secondary disabled:opacity-40">← Prev</button>
        <span className="text-gray-500 text-sm self-center">Page {page + 1} of {Math.max(1, Math.ceil(total / limit))}</span>
        <button disabled={(page + 1) * limit >= total} onClick={() => setPage(p => p + 1)} className="btn-secondary disabled:opacity-40">Next →</button>
      </div>

      {selected && <FindingModal findingId={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

