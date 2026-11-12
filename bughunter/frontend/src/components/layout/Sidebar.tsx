import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Target, Search, Globe, Server, Link2, Bug,
  Brain, FileText, History, Wrench, ShieldCheck, Activity, Settings,
  LogOut, ChevronLeft, ChevronRight, Crosshair, Layers
} from 'lucide-react'
import { useAuth } from '../../store/auth'
import { useUI } from '../../store/ui'
import { useQuery } from '@tanstack/react-query'
import { getApprovals } from '../../lib/api'

const links = [
  { to: '/', label: 'Overview', icon: LayoutDashboard },
  { to: '/programs', label: 'Programs', icon: Target },
  { to: '/batch-hunting', label: 'Batch Hunting', icon: Layers },
  { to: '/recon', label: 'Reconnaissance', icon: Search },
  { to: '/assets', label: 'Assets', icon: Globe },
  { to: '/live-hosts', label: 'Live Hosts', icon: Server },
  { to: '/endpoints', label: 'Endpoints', icon: Link2 },
  { to: '/findings', label: 'Findings', icon: Bug },
  { to: '/ai-analysis', label: 'AI Analysis', icon: Brain },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/scan-history', label: 'Scan History', icon: History },
  { to: '/tools', label: 'Tool Manager', icon: Wrench },
  { to: '/approvals', label: 'Approvals', icon: ShieldCheck, badge: true },
  { to: '/monitor', label: 'Monitor', icon: Activity },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function Sidebar() {
  const { logout } = useAuth()
  const { sidebarOpen, toggleSidebar } = useUI()
  const navigate = useNavigate()
  const { data: approvals } = useQuery({
    queryKey: ['approvals-count'],
    queryFn: () => getApprovals('pending'),
    refetchInterval: 15000,
  })
  const pendingCount = approvals?.data?.length ?? 0

  return (
    <aside className={`flex flex-col bg-dark-800 border-r border-dark-600 transition-all duration-200 ${sidebarOpen ? 'w-56' : 'w-14'}`}>
      {/* Logo */}
      <div className="flex items-center gap-2 px-3 py-4 border-b border-dark-600">
        <Crosshair className="text-accent-500 shrink-0" size={22} />
        {sidebarOpen && <span className="font-bold text-sm text-white truncate">BugHunter AI</span>}
        <button onClick={toggleSidebar} className="ml-auto text-gray-500 hover:text-gray-300">
          {sidebarOpen ? <ChevronLeft size={16} /> : <ChevronRight size={16} />}
        </button>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {links.map(({ to, label, icon: Icon, badge }) => (
          <NavLink key={to} to={to} end={to === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 mx-1 rounded-lg text-sm transition-colors relative
              ${isActive ? 'bg-accent-500/10 text-accent-500' : 'text-gray-400 hover:text-gray-200 hover:bg-dark-700'}`
            }
          >
            <Icon size={17} className="shrink-0" />
            {sidebarOpen && <span className="truncate">{label}</span>}
            {badge && pendingCount > 0 && (
              <span className={`${sidebarOpen ? 'ml-auto' : 'absolute top-1 right-1'} bg-warn-500 text-dark-900 text-xs font-bold rounded-full w-4 h-4 flex items-center justify-center`}>
                {pendingCount > 9 ? '9+' : pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Logout */}
      <button onClick={() => { logout(); navigate('/login') }}
        className="flex items-center gap-3 px-3 py-3 mx-1 mb-2 rounded-lg text-gray-500 hover:text-danger-400 hover:bg-dark-700 text-sm transition-colors">
        <LogOut size={17} className="shrink-0" />
        {sidebarOpen && <span>Logout</span>}
      </button>
    </aside>
  )
}

