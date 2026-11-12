import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getPrograms, updateProgram, createScan } from '../lib/api'
import { Activity, Play, Bell } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Monitor() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['programs'], queryFn: getPrograms })
  const programs = data?.data ?? []

  const toggleMonitor = useMutation({
    mutationFn: ({ id, enabled, cron }: any) => updateProgram(id, { monitoring_enabled: enabled, schedule_cron: cron }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['programs'] }); toast.success('Monitoring updated') }
  })

  const runNow = useMutation({
    mutationFn: (id: string) => createScan(id, { type: 'subdomains', targets: [] }),
    onSuccess: () => toast.success('Full recon scan started'),
  })

  const [crons, setCrons] = useState<Record<string, string>>({})
  const presets = [
    { label: 'Every hour', value: '0 * * * *' },
    { label: 'Every 6h', value: '0 */6 * * *' },
    { label: 'Daily', value: '0 8 * * *' },
    { label: 'Weekly', value: '0 8 * * 1' },
  ]

  return (
    <div className="p-6 space-y-6">
      <div className="card">
        <div className="flex items-center gap-2 mb-1"><Activity size={16} className="text-accent-500" /><h2 className="text-sm font-semibold text-gray-300">Continuous Monitoring</h2></div>
        <p className="text-xs text-gray-500 mb-6">Schedule automatic reconnaissance for authorized programs. All scans respect program scope and rate limits.</p>

        <div className="space-y-4">
          {programs.map((p: any) => (
            <div key={p.id} className="bg-dark-700 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div>
                  <p className="text-white font-medium">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.platform_url || 'No platform URL'}</p>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={() => runNow.mutate(p.id)} className="btn-secondary text-xs flex items-center gap-1"><Play size={11} />Run Now</button>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <div className={`relative w-10 h-5 rounded-full transition-colors ${p.monitoring_enabled ? 'bg-accent-500' : 'bg-dark-500'}`}
                      onClick={() => toggleMonitor.mutate({ id: p.id, enabled: !p.monitoring_enabled, cron: crons[p.id] || p.schedule_cron })}>
                      <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${p.monitoring_enabled ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </div>
                    <span className="text-xs text-gray-400">{p.monitoring_enabled ? 'On' : 'Off'}</span>
                  </label>
                </div>
              </div>

              {p.monitoring_enabled && (
                <div className="mt-2 space-y-2">
                  <div className="flex gap-2 flex-wrap">
                    {presets.map(pr => (
                      <button key={pr.value} onClick={() => setCrons(c => ({ ...c, [p.id]: pr.value }))} className={`text-xs px-2 py-1 rounded border transition-colors ${(crons[p.id] || p.schedule_cron) === pr.value ? 'border-accent-500 text-accent-500' : 'border-dark-500 text-gray-500 hover:border-gray-500'}`}>{pr.label}</button>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <input className="input font-mono text-xs flex-1" placeholder="Custom cron: 0 */6 * * *" value={crons[p.id] ?? p.schedule_cron ?? ''} onChange={e => setCrons(c => ({ ...c, [p.id]: e.target.value }))} />
                    <button onClick={() => toggleMonitor.mutate({ id: p.id, enabled: true, cron: crons[p.id] })} className="btn-primary text-xs">Save</button>
                  </div>
                  {(crons[p.id] || p.schedule_cron) && <p className="text-xs text-gray-600 font-mono">Schedule: {crons[p.id] || p.schedule_cron}</p>}
                </div>
              )}
            </div>
          ))}
          {programs.length === 0 && <p className="text-gray-600 text-sm text-center py-8">Add programs first to configure monitoring</p>}
        </div>
      </div>

      <div className="card">
        <div className="flex items-center gap-2 mb-4"><Bell size={16} className="text-accent-500" /><h2 className="text-sm font-semibold text-gray-300">Notifications</h2></div>
        <p className="text-xs text-gray-500">Notifications appear in the bell icon when new findings are detected during scheduled scans.</p>
      </div>
    </div>
  )
}

