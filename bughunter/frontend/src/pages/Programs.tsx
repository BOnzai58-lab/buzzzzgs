import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'
import { getPrograms, createProgram, deleteProgram, getScopeRules, addScopeRule, deleteScopeRule } from '../lib/api'
import StatusBadge from '../components/ui/StatusBadge'
import ConfirmModal from '../components/ui/ConfirmModal'
import toast from 'react-hot-toast'

function ProgramModal({ onClose, onSave }: any) {
  const [form, setForm] = useState({ name: '', platform_url: '', policy_url: '', rate_limit_rps: 1.0 })
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card max-w-md w-full mx-4">
        <h3 className="font-semibold text-white mb-4">Add Program</h3>
        <div className="space-y-3">
          {[['name', 'Program Name *'], ['platform_url', 'Platform URL'], ['policy_url', 'Policy URL']].map(([k, l]) => (
            <div key={k}><label className="label">{l}</label>
              <input className="input" value={(form as any)[k]} onChange={e => setForm(p => ({ ...p, [k]: e.target.value }))} /></div>
          ))}
          <div><label className="label">Rate Limit (req/s)</label>
            <input type="number" step="0.1" className="input" value={form.rate_limit_rps} onChange={e => setForm(p => ({ ...p, rate_limit_rps: +e.target.value }))} /></div>
        </div>
        <div className="flex gap-3 mt-6 justify-end">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button onClick={() => onSave(form)} className="btn-primary">Save</button>
        </div>
      </div>
    </div>
  )
}

function ScopeRulesPanel({ programId }: { programId: string }) {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['scope-rules', programId], queryFn: () => getScopeRules(programId) })
  const [form, setForm] = useState({ kind: 'domain', value: '', notes: '' })
  const add = useMutation({ mutationFn: () => addScopeRule(programId, form), onSuccess: () => { qc.invalidateQueries({ queryKey: ['scope-rules', programId] }); setForm(p => ({ ...p, value: '', notes: '' })); toast.success('Rule added') } })
  const del = useMutation({ mutationFn: (id: string) => deleteScopeRule(programId, id), onSuccess: () => qc.invalidateQueries({ queryKey: ['scope-rules', programId] }) })
  const kindColor: Record<string, string> = { domain: 'text-accent-500', wildcard: 'text-green-400', cidr: 'text-purple-400', exclude: 'text-danger-400' }
  return (
    <div className="mt-3 pl-4 border-l-2 border-dark-600 space-y-3">
      <div className="flex gap-2 items-end flex-wrap">
        <div><label className="label">Kind</label>
          <select className="input w-28" value={form.kind} onChange={e => setForm(p => ({ ...p, kind: e.target.value }))}>
            {['domain', 'wildcard', 'cidr', 'exclude'].map(k => <option key={k}>{k}</option>)}
          </select>
        </div>
        <div className="flex-1"><label className="label">Value</label><input className="input" placeholder="example.com" value={form.value} onChange={e => setForm(p => ({ ...p, value: e.target.value }))} /></div>
        <button className="btn-primary" onClick={() => add.mutate()}>Add</button>
      </div>
      <div className="space-y-1">
        {(data?.data ?? []).map((r: any) => (
          <div key={r.id} className="flex items-center gap-3 text-sm py-1">
            <span className={`font-mono text-xs font-bold w-16 ${kindColor[r.kind]}`}>{r.kind}</span>
            <span className="text-gray-300 flex-1 font-mono">{r.value}</span>
            <button onClick={() => del.mutate(r.id)} className="text-gray-600 hover:text-danger-400"><Trash2 size={13} /></button>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Programs() {
  const qc = useQueryClient()
  const [showModal, setShowModal] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [delTarget, setDelTarget] = useState<any>(null)
  const { data } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const create = useMutation({ mutationFn: createProgram, onSuccess: () => { qc.invalidateQueries({ queryKey: ['programs'] }); setShowModal(false); toast.success('Program created') } })
  const del = useMutation({ mutationFn: (id: string) => deleteProgram(id), onSuccess: () => { qc.invalidateQueries({ queryKey: ['programs'] }); setDelTarget(null); toast.success('Deleted') } })
  const programs = data?.data ?? []

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <p className="text-gray-400 text-sm">{programs.length} program{programs.length !== 1 ? 's' : ''}</p>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2"><Plus size={15} />Add Program</button>
      </div>

      <div className="space-y-3">
        {programs.map((p: any) => (
          <div key={p.id} className="card">
            <div className="flex items-center gap-4 cursor-pointer" onClick={() => setExpanded(expanded === p.id ? null : p.id)}>
              <div className="flex-1">
                <p className="font-semibold text-white">{p.name}</p>
                <p className="text-xs text-gray-500">{p.platform_url || 'No platform URL'} · {p.rate_limit_rps} req/s</p>
              </div>
              <StatusBadge value={p.active ? 'done' : 'stopped'} />
              <button onClick={e => { e.stopPropagation(); setDelTarget(p) }} className="text-gray-600 hover:text-danger-400"><Trash2 size={15} /></button>
              {expanded === p.id ? <ChevronUp size={16} className="text-gray-500" /> : <ChevronDown size={16} className="text-gray-500" />}
            </div>
            {expanded === p.id && <ScopeRulesPanel programId={p.id} />}
          </div>
        ))}
        {programs.length === 0 && <div className="card text-center py-12 text-gray-600">No programs yet. Add one to get started.</div>}
      </div>

      {showModal && <ProgramModal onClose={() => setShowModal(false)} onSave={(d: any) => create.mutate(d)} />}
      {delTarget && <ConfirmModal title="Delete Program" message={`Delete "${delTarget.name}"? This will remove all associated data.`} danger onConfirm={() => del.mutate(delTarget.id)} onCancel={() => setDelTarget(null)} />}
    </div>
  )
}

