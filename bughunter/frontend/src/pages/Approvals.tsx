import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getApprovals, approveRequest, rejectRequest } from '../lib/api'
import { ShieldCheck, ShieldX, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/ui/EmptyState'
import toast from 'react-hot-toast'

export default function Approvals() {
  const qc = useQueryClient()
  const { data: pending } = useQuery({ queryKey: ['approvals', 'pending'], queryFn: () => getApprovals('pending'), refetchInterval: 10000 })
  const { data: history } = useQuery({ queryKey: ['approvals', 'approved'], queryFn: () => getApprovals('approved') })
  const approve = useMutation({ mutationFn: approveRequest, onSuccess: () => { qc.invalidateQueries({ queryKey: ['approvals'] }); toast.success('Approved — verification running') } })
  const reject = useMutation({ mutationFn: rejectRequest, onSuccess: () => { qc.invalidateQueries({ queryKey: ['approvals'] }); toast.success('Rejected') } })

  const pendingItems = pending?.data ?? []
  const historyItems = history?.data ?? []

  return (
    <div className="p-6 space-y-6">
      {/* Pending */}
      <div className="card">
        <div className="flex items-center gap-2 mb-4">
          <Clock size={16} className="text-warn-500" />
          <h2 className="text-sm font-semibold text-gray-300">Pending Approvals ({pendingItems.length})</h2>
        </div>
        {pendingItems.length === 0
          ? <EmptyState icon={<ShieldCheck size={32} />} title="No pending approvals" description="All verification requests have been handled" />
          : (
            <div className="space-y-3">
              {pendingItems.map((r: any) => (
                <div key={r.id} className="bg-dark-700 rounded-lg p-4 border border-warn-500/30">
                  <p className="text-white font-medium text-sm mb-1">{r.action_description}</p>
                  <p className="text-xs text-gray-500 mb-3">
                    Requested {formatDistanceToNow(new Date(r.created_at), { addSuffix: true })} · Finding: <span className="font-mono">{r.finding_id.substring(0, 8)}…</span>
                  </p>
                  <div className="bg-dark-900 rounded p-3 mb-3 text-xs text-gray-400">
                    ⚠️ <strong className="text-warn-400">Review before approving.</strong> This will trigger a safe, non-destructive verification check on the finding. Requires analyst or admin role.
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => approve.mutate(r.id)} className="btn-primary flex items-center gap-1 text-xs"><ShieldCheck size={13} />Approve</button>
                    <button onClick={() => reject.mutate(r.id)} className="btn-danger flex items-center gap-1 text-xs"><ShieldX size={13} />Reject</button>
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>

      {/* History */}
      <div className="card">
        <h2 className="text-sm font-semibold text-gray-300 mb-4">Approval History</h2>
        {historyItems.length === 0
          ? <p className="text-gray-600 text-sm">No history yet</p>
          : (
            <table className="w-full">
              <thead><tr>
                <th className="table-header">Description</th><th className="table-header">Status</th>
                <th className="table-header">Decided</th>
              </tr></thead>
              <tbody>
                {historyItems.map((r: any) => (
                  <tr key={r.id} className="table-row">
                    <td className="table-cell text-sm">{r.action_description}</td>
                    <td className="table-cell"><StatusBadge value={r.status} /></td>
                    <td className="table-cell text-xs text-gray-500">{r.decided_at ? formatDistanceToNow(new Date(r.decided_at), { addSuffix: true }) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
      </div>
    </div>
  )
}

