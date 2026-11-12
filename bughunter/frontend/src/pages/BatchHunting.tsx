import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getBatches,
  getBatch,
  createBatch,
  importBatchTargets,
  validateBatch,
  startBatch,
  pauseBatch,
  resumeBatch,
  cancelBatch,
  getJobs,
  retryJob,
  cancelJob,
  triggerEmergencyStop,
  resetEmergencyStop,
  getEmergencyStopStatus,
  getPrograms,
  generateBatchReport,
  getSchedules,
  createSchedule,
  toggleSchedule,
} from '../lib/api'
import {
  UploadCloud,
  CheckCircle,
  AlertOctagon,
  Play,
  Pause,
  RotateCcw,
  StopCircle,
  FileText,
  Plus,
} from 'lucide-react'
import toast from 'react-hot-toast'

export default function BatchHunting() {
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<'overview' | 'import' | 'validation' | 'queue' | 'schedules' | 'reports'>('overview')
  const [selectedBatchId, setSelectedBatchId] = useState<string | null>(null)

  // Creation / Import Form States
  const [newBatchName, setNewBatchName] = useState('')
  const [importContent, setImportContent] = useState('')
  const [importFormat, setImportFormat] = useState('txt')
  const [selectedProgramId, setSelectedProgramId] = useState('')
  const [testingProfile, setTestingProfile] = useState('standard')

  // Emergency stop modal
  const [showStopModal, setShowStopModal] = useState(false)
  const [stopReason, setStopReason] = useState('Manual operator emergency stop')

  // Queries
  const { data: batchesData } = useQuery({
    queryKey: ['batches'],
    queryFn: () => getBatches(),
    refetchInterval: 5000,
  })
  const batches = batchesData?.data ?? []

  // Default to first batch if none selected
  const activeBatchId = selectedBatchId || (batches[0]?.id ? String(batches[0].id) : null)

  const { data: batchDetailData } = useQuery({
    queryKey: ['batch', activeBatchId],
    queryFn: () => (activeBatchId ? getBatch(activeBatchId) : null),
    enabled: !!activeBatchId,
    refetchInterval: 3000,
  })
  const activeBatch = batchDetailData?.data

  const { data: jobsData } = useQuery({
    queryKey: ['jobs', activeBatchId],
    queryFn: () => getJobs({ batch_id: activeBatchId }),
    enabled: !!activeBatchId,
    refetchInterval: 3000,
  })
  const jobs = jobsData?.data ?? []

  const { data: emergencyStatus, refetch: refetchStopStatus } = useQuery({
    queryKey: ['emergency-stop-status'],
    queryFn: getEmergencyStopStatus,
    refetchInterval: 5000,
  })
  const isEmergencyStopped = emergencyStatus?.data?.is_emergency_stopped ?? false

  const { data: programsData } = useQuery({
    queryKey: ['programs'],
    queryFn: getPrograms,
  })
  const programs = programsData?.data ?? []

  const { data: schedulesData } = useQuery({
    queryKey: ['schedules'],
    queryFn: () => getSchedules(),
    refetchInterval: 5000,
  })
  const schedules = schedulesData?.data ?? []

  // Mutations
  const createBatchMut = useMutation({
    mutationFn: () => createBatch({ name: newBatchName || 'Authorized Batch Assessment' }),
    onSuccess: (res: any) => {
      toast.success('Batch created!')
      setSelectedBatchId(res.data.id)
      setNewBatchName('')
      qc.invalidateQueries({ queryKey: ['batches'] })
    },
  })

  const importMut = useMutation({
    mutationFn: () =>
      importBatchTargets(activeBatchId!, {
        source_format: importFormat,
        content: importContent,
        program_id: selectedProgramId || undefined,
        testing_profile: testingProfile,
      }),
    onSuccess: (res: any) => {
      toast.success(`Imported ${res.data.imported} targets (${res.data.duplicates_skipped} duplicates skipped)`)
      setImportContent('')
      setActiveTab('validation')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Import failed'),
  })

  const validateMut = useMutation({
    mutationFn: () => validateBatch(activeBatchId!),
    onSuccess: (res: any) => {
      toast.success(`Validation finished: ${res.data.valid_targets} valid, ${res.data.rejected_targets} rejected`)
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
  })

  const startBatchMut = useMutation({
    mutationFn: () => startBatch(activeBatchId!),
    onSuccess: () => {
      toast.success('Batch queued & execution started!')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to start batch'),
  })

  const pauseBatchMut = useMutation({
    mutationFn: () => pauseBatch(activeBatchId!),
    onSuccess: () => {
      toast.success('Batch paused')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
  })

  const resumeBatchMut = useMutation({
    mutationFn: () => resumeBatch(activeBatchId!),
    onSuccess: () => {
      toast.success('Batch resumed')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
  })

  const cancelBatchMut = useMutation({
    mutationFn: () => cancelBatch(activeBatchId!),
    onSuccess: () => {
      toast.success('Batch cancelled')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
  })

  const emergencyStopMut = useMutation({
    mutationFn: () => triggerEmergencyStop({ reason: stopReason }),
    onSuccess: () => {
      toast.error('GLOBAL EMERGENCY STOP ACTIVE: All operations halted.')
      setShowStopModal(false)
      refetchStopStatus()
      qc.invalidateQueries({ queryKey: ['batches'] })
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const resetEmergencyMut = useMutation({
    mutationFn: resetEmergencyStop,
    onSuccess: () => {
      toast.success('Emergency stop cleared. Queue operational.')
      refetchStopStatus()
    },
  })

  const reportMut = useMutation({
    mutationFn: () => generateBatchReport(activeBatchId!),
    onSuccess: () => {
      toast.success('Batch Summary Report generated!')
      qc.invalidateQueries({ queryKey: ['batch', activeBatchId] })
    },
  })

  return (
    <div className="p-6 space-y-6">
      {/* ── Emergency Stop Alert Banner ── */}
      {isEmergencyStopped && (
        <div className="card bg-danger-500/20 border-danger-500 flex items-center justify-between p-4">
          <div className="flex items-center gap-3 text-danger-400">
            <AlertOctagon size={24} className="animate-pulse" />
            <div>
              <p className="font-bold text-white text-sm">GLOBAL EMERGENCY STOP ACTIVE</p>
              <p className="text-xs text-gray-300">All outbound queue dispatching and background scanning tasks are locked.</p>
            </div>
          </div>
          <button
            onClick={() => resetEmergencyMut.mutate()}
            className="btn-secondary text-xs border-danger-500/50 hover:bg-danger-500/20 text-white"
          >
            Clear Emergency Stop
          </button>
        </div>
      )}

      {/* ── Top Header & Batch Selector ── */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-white tracking-tight">Batch Hunting Center</h1>
            <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              Active Engine
            </span>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Bulk authorized target import, pre-queue verification, and persistent background assessments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {batches.length > 0 && (
            <select
              className="input text-xs w-56 font-medium"
              value={activeBatchId || ''}
              onChange={(e) => setSelectedBatchId(e.target.value)}
            >
              {batches.map((b: any) => (
                <option key={b.id} value={b.id}>
                  {b.name} ({b.status.toUpperCase()})
                </option>
              ))}
            </select>
          )}

          <button
            onClick={() => {
              const name = prompt('Enter new Batch Name:', 'Sprint Assessment Batch')
              if (name) {
                setNewBatchName(name)
                createBatchMut.mutate()
              }
            }}
            className="btn-secondary flex items-center gap-1.5 text-xs py-2"
          >
            <Plus size={14} /> New Batch
          </button>

          <button
            onClick={() => setShowStopModal(true)}
            className="btn-danger flex items-center gap-1.5 text-xs py-2"
          >
            <AlertOctagon size={14} /> Emergency Stop
          </button>
        </div>
      </div>

      {/* ── Navigation Tabs (§10.8) ── */}
      <div className="flex border-b border-dark-600 gap-1 text-xs font-medium">
        {[
          { key: 'overview', label: 'Batch Overview' },
          { key: 'import', label: 'Import Targets' },
          { key: 'validation', label: 'Authorization Validation' },
          { key: 'queue', label: 'Job Queue & Controls' },
          { key: 'schedules', label: 'Scheduled Monitoring' },
          { key: 'reports', label: 'Batch Reports' },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key as any)}
            className={`px-4 py-2.5 transition-colors border-b-2 -mb-px ${
              activeTab === tab.key
                ? 'border-accent-500 text-accent-500'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── 1. Batch Overview View (Matching User Reference Image) ── */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Mockup styled Upload box */}
          <div className="card bg-dark-800 border-dark-600 p-6">
            <div className="flex items-center gap-2 text-accent-400 mb-2">
              <UploadCloud size={20} />
              <span className="font-semibold text-sm">Upload target list</span>
            </div>
            <p className="text-xs text-gray-400 mb-3">TXT · CSV · JSON · Manual entry</p>
            <div className="inline-block bg-dark-900 border border-dark-600 rounded px-2.5 py-1 text-xs font-mono text-gray-300 mb-2">
              targets.txt
            </div>
            <p className="text-xs text-gray-500">One authorized domain or application per line.</p>
            <div className="mt-4">
              <button onClick={() => setActiveTab('import')} className="btn-primary text-xs py-1.5">
                Go to Import Targets
              </button>
            </div>
          </div>

          {/* Metric Cards (100 Targets submitted / Completed) */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="card bg-dark-800/90 border-dark-600">
              <span className="text-3xl font-extrabold text-white block">
                {activeBatch?.total_targets ?? 0}
              </span>
              <span className="text-xs text-gray-400 mt-1 block">Targets submitted</span>
            </div>
            <div className="card bg-dark-800/90 border-dark-600">
              <span className="text-3xl font-extrabold text-white block">
                {activeBatch?.completed_targets ?? 0}
              </span>
              <span className="text-xs text-gray-400 mt-1 block">Completed</span>
            </div>
            <div className="card bg-dark-800/90 border-dark-600">
              <span className="text-3xl font-extrabold text-accent-400 block">
                {activeBatch?.running_targets ?? 0}
              </span>
              <span className="text-xs text-gray-400 mt-1 block">Running</span>
            </div>
            <div className="card bg-dark-800/90 border-dark-600">
              <span className="text-3xl font-extrabold text-danger-400 block">
                {activeBatch?.failed_targets ?? 0}
              </span>
              <span className="text-xs text-gray-400 mt-1 block">Failed</span>
            </div>
          </div>

          {/* Queue List Preview (Matching Image) */}
          <div className="card bg-dark-800 border-dark-600">
            <h3 className="text-sm font-semibold text-white mb-4">Queue</h3>
            {jobs.length === 0 ? (
              <p className="text-xs text-gray-500 py-4">No jobs currently queued. Import and validate targets to begin.</p>
            ) : (
              <div className="space-y-3">
                {jobs.slice(0, 8).map((j: any) => {
                  let pillClass = 'bg-dark-700 text-gray-400'
                  if (j.status === 'running') pillClass = 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  if (j.status === 'completed') pillClass = 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  if (j.status === 'failed') pillClass = 'bg-danger-500/20 text-danger-400 border border-danger-500/30'
                  return (
                    <div key={j.id} className="flex items-center justify-between py-2 border-b border-dark-700/60 last:border-0">
                      <span className="font-mono text-sm text-gray-200">{j.target_value}</span>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium capitalize ${pillClass}`}>
                        {j.status}
                      </span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── 2. Import Targets View ── */}
      {activeTab === 'import' && (
        <div className="card space-y-4 max-w-3xl">
          <h2 className="text-base font-semibold text-white">Import Target List</h2>
          <p className="text-xs text-gray-400">
            Submit multiple explicitly authorized websites, applications, domains, APIs, or IP ranges in one batch.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="label">Associated Program (Optional)</label>
              <select
                className="input text-xs"
                value={selectedProgramId}
                onChange={(e) => setSelectedProgramId(e.target.value)}
              >
                <option value="">Auto-match via scope rules</option>
                {programs.map((p: any) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label">Format</label>
              <select
                className="input text-xs"
                value={importFormat}
                onChange={(e) => setImportFormat(e.target.value)}
              >
                <option value="txt">Plain Text (One per line)</option>
                <option value="csv">Structured CSV</option>
                <option value="json">JSON Array</option>
              </select>
            </div>

            <div>
              <label className="label">Testing Profile</label>
              <select
                className="input text-xs"
                value={testingProfile}
                onChange={(e) => setTestingProfile(e.target.value)}
              >
                <option value="standard">Standard (Recon + Vuln)</option>
                <option value="passive_only">Passive Only</option>
                <option value="full">Full (Active verification)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="label">Target Content</label>
            <textarea
              rows={8}
              className="input font-mono text-xs"
              placeholder={`example-one.com\nexample-two.com\napi.example-three.com\n192.168.1.0/24`}
              value={importContent}
              onChange={(e) => setImportContent(e.target.value)}
            />
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => importMut.mutate()}
              disabled={importMut.isPending || !importContent.trim()}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <UploadCloud size={14} /> Import Targets to Batch
            </button>
          </div>
        </div>
      )}

      {/* ── 3. Authorization Validation View ── */}
      {activeTab === 'validation' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Target Authorization & Scope Validation</h2>
              <p className="text-xs text-gray-400">
                Every imported target is individually verified against program scope, exclusions, and active policies.
              </p>
            </div>
            <button
              onClick={() => validateMut.mutate()}
              disabled={validateMut.isPending}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <CheckCircle size={14} /> Validate All Targets
            </button>
          </div>

          <div className="card overflow-x-auto p-0">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-dark-600 bg-dark-700/50">
                  <th className="table-header">Normalized Target</th>
                  <th className="table-header">Type</th>
                  <th className="table-header">Eligibility Status</th>
                  <th className="table-header">Scope / Rejection Reason</th>
                </tr>
              </thead>
              <tbody>
                {(activeBatch?.targets ?? []).length === 0 ? (
                  <tr>
                    <td colSpan={4} className="p-6 text-center text-xs text-gray-500">
                      No targets imported yet.
                    </td>
                  </tr>
                ) : (
                  (activeBatch?.targets ?? []).map((t: any) => {
                    let statusColor = 'text-gray-400 bg-dark-700'
                    if (t.eligibility_status === 'VALIDATED') statusColor = 'text-emerald-400 bg-emerald-500/10'
                    if (t.eligibility_status === 'EXCLUDED') statusColor = 'text-danger-400 bg-danger-500/10'
                    if (t.eligibility_status === 'OUT_OF_SCOPE') statusColor = 'text-warn-400 bg-warn-500/10'
                    if (t.eligibility_status === 'READY_TO_QUEUE') statusColor = 'text-cyan-400 bg-cyan-500/10'
                    return (
                      <tr key={t.id} className="table-row">
                        <td className="table-cell font-mono font-medium text-white">{t.normalized_target}</td>
                        <td className="table-cell uppercase text-[11px] text-gray-400">{t.target_type}</td>
                        <td className="table-cell">
                          <span className={`px-2 py-0.5 rounded text-[11px] font-semibold ${statusColor}`}>
                            {t.eligibility_status}
                          </span>
                        </td>
                        <td className="table-cell text-xs text-gray-400">
                          {t.rejection_reason || 'In-Scope & Authorized'}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button
              onClick={() => startBatchMut.mutate()}
              disabled={startBatchMut.isPending || activeBatch?.valid_targets === 0}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <Play size={14} /> Start Execution ({activeBatch?.valid_targets ?? 0} Eligible)
            </button>
          </div>
        </div>
      )}

      {/* ── 4. Job Queue & Controls View ── */}
      {activeTab === 'queue' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Assessment Job Queue</h2>
              <p className="text-xs text-gray-400">
                Persistent background execution with per-program rate limits and concurrency caps.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {activeBatch?.status === 'running' ? (
                <button
                  onClick={() => pauseBatchMut.mutate()}
                  className="btn-secondary text-xs flex items-center gap-1"
                >
                  <Pause size={14} /> Pause Batch
                </button>
              ) : activeBatch?.status === 'paused' ? (
                <button
                  onClick={() => resumeBatchMut.mutate()}
                  className="btn-primary text-xs flex items-center gap-1"
                >
                  <Play size={14} /> Resume Batch
                </button>
              ) : (
                <button
                  onClick={() => startBatchMut.mutate()}
                  className="btn-primary text-xs flex items-center gap-1"
                >
                  <Play size={14} /> Start Batch
                </button>
              )}
              <button
                onClick={() => cancelBatchMut.mutate()}
                className="btn-secondary text-xs text-danger-400 hover:text-danger-300"
              >
                Cancel Batch
              </button>
            </div>
          </div>

          <div className="card overflow-x-auto p-0">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-dark-600 bg-dark-700/50">
                  <th className="table-header">Target</th>
                  <th className="table-header">Status</th>
                  <th className="table-header">Stage</th>
                  <th className="table-header">Progress</th>
                  <th className="table-header">Duration</th>
                  <th className="table-header">Actions</th>
                </tr>
              </thead>
              <tbody>
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="p-6 text-center text-xs text-gray-500">
                      No jobs active in queue.
                    </td>
                  </tr>
                ) : (
                  jobs.map((j: any) => (
                    <tr key={j.id} className="table-row">
                      <td className="table-cell font-mono text-white">{j.target_value}</td>
                      <td className="table-cell capitalize text-xs">
                        <span
                          className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                            j.status === 'completed'
                              ? 'text-cyan-400 bg-cyan-500/10'
                              : j.status === 'running'
                              ? 'text-emerald-400 bg-emerald-500/10'
                              : j.status === 'failed'
                              ? 'text-danger-400 bg-danger-500/10'
                              : 'text-gray-400 bg-dark-700'
                          }`}
                        >
                          {j.status}
                        </span>
                      </td>
                      <td className="table-cell text-xs font-mono text-gray-400">
                        {j.current_stage || 'queued'}
                      </td>
                      <td className="table-cell text-xs text-gray-300">
                        <div className="w-24 bg-dark-700 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-accent-500 h-full transition-all"
                            style={{ width: `${j.progress}%` }}
                          />
                        </div>
                      </td>
                      <td className="table-cell text-xs font-mono text-gray-400">
                        {j.execution_time_seconds}s
                      </td>
                      <td className="table-cell">
                        {j.status === 'failed' && (
                          <button
                            onClick={() => retryJob(j.id).then(() => qc.invalidateQueries({ queryKey: ['jobs'] }))}
                            className="text-xs text-accent-400 hover:underline flex items-center gap-1"
                          >
                            <RotateCcw size={12} /> Retry
                          </button>
                        )}
                        {j.status === 'running' && (
                          <button
                            onClick={() => cancelJob(j.id).then(() => qc.invalidateQueries({ queryKey: ['jobs'] }))}
                            className="text-xs text-danger-400 hover:underline flex items-center gap-1"
                          >
                            <StopCircle size={12} /> Stop
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── 5. Scheduled Monitoring View (§10.7) ── */}
      {activeTab === 'schedules' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-base font-semibold text-white">Scheduled Passive Monitoring</h2>
              <p className="text-xs text-gray-400">
                Continuous automated discovery, asset change monitoring, and technology fingerprinting with quiet hours.
              </p>
            </div>
            <button
              onClick={() => {
                if (!programs[0]?.id) return toast.error('Create a program first')
                createSchedule({
                  name: 'Nightly Passive Discovery',
                  program_id: programs[0].id,
                  cron_expression: '0 2 * * *',
                  quiet_hours_start: '09:00',
                  quiet_hours_end: '17:00',
                }).then(() => {
                  toast.success('Schedule created')
                  qc.invalidateQueries({ queryKey: ['schedules'] })
                })
              }}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <Plus size={14} /> Add Passive Schedule
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {schedules.map((s: any) => (
              <div key={s.id} className="card border-dark-600 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-white text-sm">{s.name}</span>
                  <button
                    onClick={() => toggleSchedule(s.id).then(() => qc.invalidateQueries({ queryKey: ['schedules'] }))}
                    className={`px-2 py-0.5 rounded text-xs font-semibold ${
                      s.active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-dark-700 text-gray-500'
                    }`}
                  >
                    {s.active ? 'ACTIVE' : 'PAUSED'}
                  </button>
                </div>
                <div className="text-xs text-gray-400 space-y-1 font-mono">
                  <p>Cron: {s.cron_expression} ({s.timezone_str})</p>
                  <p>Quiet Hours: {s.quiet_hours_start || 'None'} - {s.quiet_hours_end || 'None'}</p>
                  <p>Rate Limit: {s.rate_limit_rps} rps · Max: {s.max_duration_minutes}m</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 6. Batch Reports View (§10.11) ── */}
      {activeTab === 'reports' && (
        <div className="card space-y-4 max-w-3xl">
          <h2 className="text-base font-semibold text-white">Batch Summary Reports</h2>
          <p className="text-xs text-gray-400">
            Generate and export multi-format assessment reports (PDF, Markdown, JSON, CSV).
          </p>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => reportMut.mutate()}
              disabled={reportMut.isPending}
              className="btn-primary text-xs flex items-center gap-1.5"
            >
              <FileText size={14} /> Generate Summary Report
            </button>
          </div>

          {reportMut.data?.data && (
            <div className="mt-4 p-4 rounded-lg bg-dark-900 border border-dark-600 space-y-3">
              <h3 className="font-semibold text-white text-sm">{reportMut.data.data.title}</h3>
              <pre className="text-xs font-mono text-gray-300 max-h-64 overflow-y-auto whitespace-pre-wrap">
                {reportMut.data.data.markdown_content}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* ── Emergency Stop Modal ── */}
      {showStopModal && (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
          <div className="card max-w-md w-full border-danger-500/50 space-y-4">
            <div className="flex items-center gap-3 text-danger-400">
              <AlertOctagon size={28} />
              <h3 className="font-bold text-white text-base">Confirm Global Emergency Stop</h3>
            </div>
            <p className="text-xs text-gray-300">
              This action immediately terminates all running security checks, closes the outbound egress path, cancels queued targets, and logs an immutable audit event.
            </p>
            <div>
              <label className="label">Reason for Emergency Stop</label>
              <input
                className="input text-xs"
                value={stopReason}
                onChange={(e) => setStopReason(e.target.value)}
              />
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button onClick={() => setShowStopModal(false)} className="btn-secondary text-xs">
                Cancel
              </button>
              <button
                onClick={() => emergencyStopMut.mutate()}
                disabled={emergencyStopMut.isPending}
                className="btn-danger text-xs font-bold"
              >
                Trigger Immediate Stop
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
