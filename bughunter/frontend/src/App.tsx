import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useEffect } from 'react'
import Sidebar from './components/layout/Sidebar'
import TopBar from './components/layout/TopBar'
import { useAuth } from './store/auth'

import Login from './pages/Login'
import Overview from './pages/Overview'
import Programs from './pages/Programs'
import BatchHunting from './pages/BatchHunting'
import Reconnaissance from './pages/Reconnaissance'
import Assets from './pages/Assets'
import LiveHosts from './pages/LiveHosts'
import Endpoints from './pages/Endpoints'
import Findings from './pages/Findings'
import AIAnalysis from './pages/AIAnalysis'
import Reports from './pages/Reports'
import ScanHistory from './pages/ScanHistory'
import ToolManager from './pages/ToolManager'
import Approvals from './pages/Approvals'
import Monitor from './pages/Monitor'
import Settings from './pages/Settings'

const qc = new QueryClient({ defaultOptions: { queries: { staleTime: 10000, retry: 1 } } })

function Layout() {
  const { token, loadUser } = useAuth()
  useEffect(() => { if (token) loadUser() }, [])
  if (!token) return <Navigate to="/login" replace />
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-y-auto"><Outlet /></main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route path="/" element={<Overview />} />
            <Route path="/programs" element={<Programs />} />
            <Route path="/batch-hunting" element={<BatchHunting />} />
            <Route path="/recon" element={<Reconnaissance />} />
            <Route path="/assets" element={<Assets />} />
            <Route path="/live-hosts" element={<LiveHosts />} />
            <Route path="/endpoints" element={<Endpoints />} />
            <Route path="/findings" element={<Findings />} />
            <Route path="/ai-analysis" element={<AIAnalysis />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/scan-history" element={<ScanHistory />} />
            <Route path="/tools" element={<ToolManager />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/monitor" element={<Monitor />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" toastOptions={{ style: { background: '#0d1225', color: '#e5e7eb', border: '1px solid #1c2645' } }} />
    </QueryClientProvider>
  )
}
