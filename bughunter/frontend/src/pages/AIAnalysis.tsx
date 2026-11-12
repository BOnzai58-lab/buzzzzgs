import { useQuery } from '@tanstack/react-query'
import { getFindings, getFinding } from '../lib/api'
import { useState } from 'react'
import Badge from '../components/ui/Badge'
import { Brain } from 'lucide-react'
import EmptyState from '../components/ui/EmptyState'

export default function AIAnalysis() {
  const [selected, setSelected] = useState<string | null>(null)
  const { data } = useQuery({ queryKey: ['findings-for-ai'], queryFn: () => getFindings({ limit: 50 }) })
  const { data: detail } = useQuery({ queryKey: ['finding', selected], queryFn: () => getFinding(selected!), enabled: !!selected })
  const items = data?.data?.items ?? []
  const analysis = detail?.data

  return (
    <div className="p-6 flex gap-6 h-full">
      {/* List */}
      <div className="w-72 shrink-0 space-y-2 overflow-y-auto">
        {items.length === 0 && <EmptyState icon={<Brain size={32} />} title="No findings" description="Run vulnerability scan first" />}
        {items.map((f: any) => (
          <div key={f.id} onClick={() => setSelected(f.id)} className={`card cursor-pointer transition-colors ${selected === f.id ? 'border-accent-500' : ''}`}>
            <p className="text-sm text-white font-medium truncate">{f.name}</p>
            <div className="flex gap-2 mt-1"><Badge value={f.severity} /></div>
          </div>
        ))}
      </div>

      {/* Detail */}
      <div className="flex-1 overflow-y-auto">
        {!selected && <EmptyState icon={<Brain size={40} />} title="Select a finding" description="Click a finding to view AI analysis" />}
        {selected && analysis && (() => {
          const f = analysis.finding
          return (
            <div className="space-y-4">
              <div className="card">
                <h2 className="font-semibold text-white mb-1">{f?.name}</h2>
                <p className="text-xs text-gray-500">Finding ID: {selected}</p>
              </div>
              {analysis.evidence?.length === 0 && (
                <div className="card border-warn-500/40">
                  <p className="text-warn-400 text-sm">⚠️ No AI analysis yet. Click "AI Analysis" on the finding to request one.</p>
                </div>
              )}
              {(analysis.evidence ?? []).length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3">Evidence ({analysis.evidence.length})</h3>
                  <div className="space-y-2">
                    {analysis.evidence.map((e: any) => (
                      <div key={e.id} className="bg-dark-900 rounded p-3 text-xs font-mono">
                        <span className="text-accent-500">[{e.kind}]</span> <span className="text-gray-400">{e.content_ref}</span>
                        <div className="text-gray-600 mt-1">SHA256: {e.sha256}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {(analysis.validation_history ?? []).length > 0 && (
                <div className="card">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3">Validation History</h3>
                  <div className="space-y-2">
                    {analysis.validation_history.map((h: any, i: number) => (
                      <div key={i} className="text-xs text-gray-500 border-l-2 border-dark-500 pl-3">
                        <span className="text-gray-400">{h.from}</span> → <span className="text-white font-medium">{h.to}</span>
                        <span className="text-gray-600 ml-2">{new Date(h.at).toLocaleString()}</span>
                        {h.reason && <span className="text-gray-600 ml-2">— {h.reason}</span>}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })()}
      </div>
    </div>
  )
}

