import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTools,
  getToolSystemInfo,
  getToolLogs,
  installTool,
  updateTool,
  installAllTools,
  updateAllTools,
} from '../lib/api'
import {
  CheckCircle,
  XCircle,
  Download,
  RefreshCw,
  Terminal,
  Server,
  ArrowUpCircle,
  AlertTriangle,
  X,
  ExternalLink,
} from 'lucide-react'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import toast from 'react-hot-toast'

export default function ToolManager() {
  const qc = useQueryClient()
  const [selectedToolLogs, setSelectedToolLogs] = useState<string | null>(null)

  // 1. Fetch Tools Status
  const { data: toolsData, isLoading: toolsLoading, refetch: refetchTools } = useQuery({
    queryKey: ['tools'],
    queryFn: getTools,
    refetchInterval: 5000,
  })

  // 2. Fetch System Environment Information
  const { data: sysData } = useQuery({
    queryKey: ['tool-system-info'],
    queryFn: getToolSystemInfo,
  })

  // 3. Fetch Selected Tool Logs
  const { data: logData } = useQuery({
    queryKey: ['tool-logs', selectedToolLogs],
    queryFn: () => (selectedToolLogs ? getToolLogs(selectedToolLogs) : null),
    enabled: !!selectedToolLogs,
    refetchInterval: selectedToolLogs ? 2000 : false,
  })

  const tools = toolsData?.data ?? []
  const sysInfo = sysData?.data ?? {}
  const installedCount = tools.filter((t: any) => t.installed).length

  // Mutations
  const installMut = useMutation({
    mutationFn: (name: string) => installTool(name),
    onSuccess: (_, name) => {
      toast.success(`Started installation for ${name}`)
      setSelectedToolLogs(name)
      qc.invalidateQueries({ queryKey: ['tools'] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Install failed'),
  })

  const updateMut = useMutation({
    mutationFn: (name: string) => updateTool(name),
    onSuccess: (_, name) => {
      toast.success(`Started update for ${name}`)
      setSelectedToolLogs(name)
      qc.invalidateQueries({ queryKey: ['tools'] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Update failed'),
  })

  const installAllMut = useMutation({
    mutationFn: installAllTools,
    onSuccess: (res: any) => {
      toast.success(`Queued installs: ${res.data.tools?.join(', ') || 'None needed'}`)
      qc.invalidateQueries({ queryKey: ['tools'] })
    },
    onError: () => toast.error('Failed to trigger bulk install'),
  })

  const updateAllMut = useMutation({
    mutationFn: updateAllTools,
    onSuccess: () => {
      toast.success('Queued updates for all tools')
      qc.invalidateQueries({ queryKey: ['tools'] })
    },
    onError: () => toast.error('Failed to trigger bulk update'),
  })

  return (
    <div className="p-6 space-y-6">
      {/* ── System Environment Banner ── */}
      <div className="card bg-dark-800/80 border border-dark-600">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-accent-500/10 text-accent-500">
              <Server size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-semibold text-white text-sm">
                  {sysInfo.distribution || 'Linux Host'} ({sysInfo.architecture || 'x86_64'})
                </h2>
                {sysInfo.is_kali && (
                  <span className="px-2 py-0.5 text-xs font-semibold rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                    Kali Linux
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Go: <span className="text-gray-300 font-mono">{sysInfo.go_version || 'Not detected'}</span> · 
                Python: <span className="text-gray-300 font-mono">{sysInfo.python_version?.slice(0, 20) || 'Active'}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-400">
              <strong className="text-white">{installedCount}</strong> of {tools.length} Tools Ready
            </span>
            <button
              onClick={() => refetchTools()}
              className="btn-secondary flex items-center gap-1.5 text-xs py-1.5"
            >
              <RefreshCw size={14} /> Refresh Status
            </button>
            <button
              onClick={() => installAllMut.mutate()}
              disabled={installAllMut.isPending}
              className="btn-primary flex items-center gap-1.5 text-xs py-1.5"
            >
              <Download size={14} /> Install Missing
            </button>
            <button
              onClick={() => updateAllMut.mutate()}
              disabled={updateAllMut.isPending}
              className="btn-secondary flex items-center gap-1.5 text-xs py-1.5"
            >
              <ArrowUpCircle size={14} /> Update All
            </button>
          </div>
        </div>

        {/* Path Alert if Go bin is not found */}
        {!sysInfo.go_installed && (
          <div className="mt-4 p-3 rounded-lg bg-warn-500/10 border border-warn-500/30 flex items-center gap-2.5 text-warn-400 text-xs">
            <AlertTriangle size={16} className="shrink-0" />
            <span>
              Go compiler was not detected in system PATH. Run <code>./scripts/install_kali.sh</code> in terminal or <code>sudo apt install golang-go</code>.
            </span>
          </div>
        )}
      </div>

      {toolsLoading && (
        <div className="flex justify-center py-16">
          <LoadingSpinner />
        </div>
      )}

      {/* ── Tools Grid (12 Tools) ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {tools.map((t: any) => {
          const isInstalling = t.status === 'Installing'
          return (
            <div
              key={t.name}
              className={`card flex flex-col justify-between border transition-all ${
                t.installed
                  ? 'border-dark-600 hover:border-dark-500'
                  : 'border-danger-500/30 bg-danger-500/5'
              }`}
            >
              <div>
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-white text-base">{t.name}</span>
                    {t.category && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-dark-700 text-gray-400">
                        {t.category}
                      </span>
                    )}
                  </div>
                  <div>
                    {isInstalling ? (
                      <span className="flex items-center gap-1 text-xs text-accent-400 font-medium">
                        <RefreshCw size={14} className="animate-spin" /> Installing
                      </span>
                    ) : t.installed ? (
                      <span className="flex items-center gap-1 text-xs text-success-400 font-medium">
                        <CheckCircle size={16} /> Installed
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-danger-400 font-medium">
                        <XCircle size={16} /> Missing
                      </span>
                    )}
                  </div>
                </div>

                <p className="text-xs text-gray-400 line-clamp-2 mb-3">
                  {t.description || 'Security utility for reconnaissance and vulnerability assessment.'}
                </p>

                {t.installed && t.version && (
                  <div className="bg-dark-900/80 rounded px-2.5 py-1.5 mb-3 font-mono text-[11px] text-gray-300 truncate">
                    {t.version}
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-dark-600/80 flex items-center justify-between gap-2">
                <button
                  onClick={() => setSelectedToolLogs(t.name)}
                  className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
                >
                  <Terminal size={14} /> Logs
                </button>

                <div className="flex items-center gap-2">
                  {t.doc_url && (
                    <a
                      href={t.doc_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-gray-500 hover:text-gray-300"
                      title="View Upstream Repository"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}

                  {t.installed ? (
                    <button
                      onClick={() => updateMut.mutate(t.name)}
                      disabled={isInstalling || updateMut.isPending}
                      className="px-2.5 py-1 rounded bg-dark-700 hover:bg-dark-600 text-xs text-gray-200 transition-colors flex items-center gap-1"
                    >
                      <ArrowUpCircle size={13} /> Update
                    </button>
                  ) : (
                    <button
                      onClick={() => installMut.mutate(t.name)}
                      disabled={isInstalling || installMut.isPending}
                      className="px-3 py-1 rounded bg-accent-500 hover:bg-accent-600 text-dark-900 font-semibold text-xs transition-colors flex items-center gap-1"
                    >
                      <Download size={13} /> Install
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Live Installation Logs Modal ── */}
      {selectedToolLogs && (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4">
          <div className="card max-w-2xl w-full flex flex-col h-[520px] border-dark-500 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-dark-600">
              <div className="flex items-center gap-2">
                <Terminal size={18} className="text-accent-500" />
                <h3 className="font-semibold text-white text-sm font-mono">
                  Execution Logs: {selectedToolLogs}
                </h3>
              </div>
              <button
                onClick={() => setSelectedToolLogs(null)}
                className="text-gray-400 hover:text-white"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto bg-dark-900 p-3 rounded-lg font-mono text-xs space-y-1.5 my-3">
              {(!logData?.data?.logs || logData.data.logs.length === 0) && (
                <p className="text-gray-600">No active execution logs yet for this tool.</p>
              )}
              {(logData?.data?.logs ?? []).map((l: any, i: number) => {
                let color = 'text-gray-300'
                if (l.level === 'WARN') color = 'text-warn-400'
                if (l.level === 'ERROR') color = 'text-danger-400'
                if (l.level === 'SUCCESS') color = 'text-success-400'
                return (
                  <div key={i} className="flex items-start gap-2">
                    <span className="text-gray-600 shrink-0">{l.timestamp}</span>
                    <span className={color}>{l.message}</span>
                  </div>
                )
              })}
            </div>

            <div className="flex justify-between items-center pt-2">
              <span className="text-xs text-gray-500">Live stream updating every 2s</span>
              <button onClick={() => setSelectedToolLogs(null)} className="btn-secondary text-xs">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
