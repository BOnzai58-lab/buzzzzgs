import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getReports, getReport, updateReport } from '../lib/api'
import StatusBadge from '../components/ui/StatusBadge'
import EmptyState from '../components/ui/EmptyState'
import { FileText, Download, Edit, Save, X } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import toast from 'react-hot-toast'

export default function Reports() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<any>(null)
  const [editing, setEditing] = useState(false)
  const [editText, setEditText] = useState('')
  const { data } = useQuery({ queryKey: ['reports'], queryFn: getReports })
  const { data: detail } = useQuery({ queryKey: ['report', selected?.id], queryFn: () => getReport(selected.id), enabled: !!selected })
  const save = useMutation({ mutationFn: () => updateReport(selected.id, { markdown: editText }), onSuccess: () => { qc.invalidateQueries({ queryKey: ['report', selected.id] }); setEditing(false); toast.success('Saved') } })
  const items = data?.data?.items ?? []
  const md = detail?.data?.markdown || ''

  const downloadMd = () => {
    const blob = new Blob([md], { type: 'text/markdown' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `report-${selected?.id}.md`; a.click()
  }

  return (
    <div className="p-6 flex gap-6 h-full">
      {/* List */}
      <div className="w-72 shrink-0 space-y-2 overflow-y-auto">
        {items.length === 0 && <EmptyState icon={<FileText size={32} />} title="No reports" description="Generate a report from a finding" />}
        {items.map((r: any) => (
          <div key={r.id} onClick={() => { setSelected(r); setEditing(false) }} className={`card cursor-pointer transition-colors ${selected?.id === r.id ? 'border-accent-500' : ''}`}>
            <p className="text-xs font-mono text-gray-500 truncate">{r.id}</p>
            <div className="flex gap-2 mt-2 items-center justify-between">
              <StatusBadge value={r.status} />
              <span className="text-xs text-gray-600">{formatDistanceToNow(new Date(r.created_at), { addSuffix: true })}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Viewer */}
      <div className="flex-1 overflow-y-auto">
        {!selected && <EmptyState icon={<FileText size={40} />} title="Select a report" description="Click a report to view or edit" />}
        {selected && (
          <div className="card h-full flex flex-col">
            <div className="flex items-center gap-3 mb-4 shrink-0">
              <span className="text-sm font-semibold text-white">Report</span>
              <StatusBadge value={detail?.data?.status || ''} />
              <div className="ml-auto flex gap-2">
                <button onClick={downloadMd} className="btn-secondary text-xs flex items-center gap-1"><Download size={12} />MD</button>
                {!editing
                  ? <button onClick={() => { setEditing(true); setEditText(md) }} className="btn-secondary text-xs flex items-center gap-1"><Edit size={12} />Edit</button>
                  : <>
                      <button onClick={() => save.mutate()} className="btn-primary text-xs flex items-center gap-1"><Save size={12} />Save</button>
                      <button onClick={() => setEditing(false)} className="btn-secondary text-xs"><X size={12} /></button>
                    </>}
              </div>
            </div>
            {editing
              ? <textarea className="input flex-1 font-mono text-xs resize-none" value={editText} onChange={e => setEditText(e.target.value)} />
              : <pre className="flex-1 overflow-auto text-xs text-gray-300 whitespace-pre-wrap font-mono bg-dark-900 rounded p-4">{md}</pre>}
          </div>
        )}
      </div>
    </div>
  )
}

