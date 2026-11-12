import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000/api/v1' })

api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('token')
  if (token) cfg.headers.Authorization = `Bearer ${token}`
  return cfg
})

api.interceptors.response.use(r => r, err => {
  if (err.response?.status === 401) { localStorage.removeItem('token'); window.location.href = '/login' }
  return Promise.reject(err)
})

export default api

// Auth
export const login = (email: string, password: string) =>
  api.post('/auth/token', new URLSearchParams({ username: email, password }), { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } })
export const getMe = () => api.get('/auth/me')
export const register = (data: any) => api.post('/auth/register', data)

// Programs
export const getPrograms = () => api.get('/programs')
export const createProgram = (data: any) => api.post('/programs', data)
export const updateProgram = (id: string, data: any) => api.patch(`/programs/${id}`, data)
export const deleteProgram = (id: string) => api.delete(`/programs/${id}`)
export const getScopeRules = (id: string) => api.get(`/programs/${id}/scope-rules`)
export const addScopeRule = (id: string, data: any) => api.post(`/programs/${id}/scope-rules`, data)
export const deleteScopeRule = (progId: string, ruleId: string) => api.delete(`/programs/${progId}/scope-rules/${ruleId}`)
export const checkScope = (data: any) => api.post('/scope/check', data)

// Scans
export const createScan = (programId: string, data: any) => api.post(`/programs/${programId}/scans`, data)
export const getScan = (id: string) => api.get(`/scans/${id}`)
export const listScans = (params?: any) => api.get('/scans', { params })
export const stopScan = (id: string) => api.post(`/scans/${id}/stop`)

// Data
export const getAssets = (params?: any) => api.get('/assets', { params })
export const getLiveHosts = (params?: any) => api.get('/live-hosts', { params })
export const getEndpoints = (params?: any) => api.get('/endpoints', { params })
export const getFindings = (params?: any) => api.get('/findings', { params })
export const getReports = (params?: any) => api.get('/reports', { params })
export const getAuditLogs = (params?: any) => api.get('/audit-logs', { params })
export const getOverviewStats = () => api.get('/stats/overview')
export const getNotifications = () => api.get('/notifications')

// Findings
export const getFinding = (id: string) => api.get(`/findings/${id}`)
export const analyzeFinding = (id: string) => api.post(`/findings/${id}/analyze`)
export const updateFindingStatus = (id: string, data: any) => api.post(`/findings/${id}/status`, data)
export const requestVerification = (id: string) => api.post(`/findings/${id}/verify`)
export const generateReport = (id: string) => api.post(`/findings/${id}/report`)

// Reports
export const getReport = (id: string, format = 'md') => api.get(`/reports/${id}`, { params: { format } })
export const updateReport = (id: string, data: any) => api.patch(`/reports/${id}`, data)

// Tools (Upgraded Linux Native Manager)
export const getTools = () => api.get('/tools')
export const getToolSystemInfo = () => api.get('/tools/system-info')
export const getToolLogs = (name: string) => api.get(`/tools/${name}/logs`)
export const installTool = (name: string) => api.post(`/tools/${name}/install`)
export const updateTool = (name: string) => api.post(`/tools/${name}/update`)
export const installAllTools = () => api.post('/tools/install-all')
export const updateAllTools = () => api.post('/tools/update-all')

// Approvals
export const getApprovals = (status = 'pending') => api.get('/approvals', { params: { status } })
export const approveRequest = (id: string, data?: any) => api.post(`/approvals/${id}/approve`, data)
export const rejectRequest = (id: string, data?: any) => api.post(`/approvals/${id}/reject`, data)

// Batch Hunting (§10)
export const getBatches = (params?: any) => api.get('/batches', { params })
export const getBatch = (id: string) => api.get(`/batches/${id}`)
export const createBatch = (data: any) => api.post('/batches', data)
export const importBatchTargets = (id: string, data: any) => api.post(`/batches/${id}/import`, data)
export const validateBatch = (id: string) => api.post(`/batches/${id}/validate`)
export const startBatch = (id: string) => api.post(`/batches/${id}/start`)
export const pauseBatch = (id: string) => api.post(`/batches/${id}/pause`)
export const resumeBatch = (id: string) => api.post(`/batches/${id}/resume`)
export const cancelBatch = (id: string) => api.post(`/batches/${id}/cancel`)
export const deleteBatchTarget = (batchId: string, targetId: string) => api.delete(`/batches/${batchId}/targets/${targetId}`)
export const generateBatchReport = (id: string) => api.post(`/batches/${id}/report`)

// Jobs & Telemetry (§10)
export const getJobs = (params?: any) => api.get('/jobs', { params })
export const getJobDetail = (id: string) => api.get(`/jobs/${id}`)
export const retryJob = (id: string) => api.post(`/jobs/${id}/retry`)
export const cancelJob = (id: string) => api.post(`/jobs/${id}/cancel`)
export const triggerEmergencyStop = (data: any) => api.post('/emergency-stop', data)
export const resetEmergencyStop = () => api.post('/emergency-stop/reset')
export const getEmergencyStopStatus = () => api.get('/emergency-stop/status')
export const getWorkers = () => api.get('/workers')
export const getSchedules = (params?: any) => api.get('/schedules', { params })
export const createSchedule = (data: any) => api.post('/schedules', data)
export const toggleSchedule = (id: string) => api.patch(`/schedules/${id}/toggle`)
export const deleteSchedule = (id: string) => api.delete(`/schedules/${id}`)
