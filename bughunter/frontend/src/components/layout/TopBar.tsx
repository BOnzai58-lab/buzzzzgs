import { Bell } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { useAuth } from '../../store/auth'

const titles: Record<string, string> = {
  '/': 'Overview', '/programs': 'Programs', '/recon': 'Reconnaissance',
  '/assets': 'Assets', '/live-hosts': 'Live Hosts', '/endpoints': 'Endpoints',
  '/findings': 'Findings', '/ai-analysis': 'AI Analysis', '/reports': 'Reports',
  '/scan-history': 'Scan History', '/tools': 'Tool Manager',
  '/approvals': 'Approvals', '/monitor': 'Monitor', '/settings': 'Settings',
}

const roleBg: Record<string, string> = {
  admin: 'bg-danger-500/20 text-danger-400 border border-danger-500/40',
  analyst: 'bg-accent-500/20 text-accent-500 border border-accent-500/40',
  viewer: 'bg-gray-500/20 text-gray-400 border border-gray-500/40',
}

export default function TopBar() {
  const { pathname } = useLocation()
  const { user } = useAuth()
  const title = titles[pathname] || 'BugHunter AI'

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-dark-800 border-b border-dark-600 shrink-0">
      <h1 className="text-lg font-semibold text-white">{title}</h1>
      <div className="flex items-center gap-3">
        {user && (
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${roleBg[user.role] || ''}`}>
            {user.role}
          </span>
        )}
        <span className="text-xs text-gray-500">{user?.email}</span>
        <Bell size={18} className="text-gray-500 cursor-pointer hover:text-gray-300" />
      </div>
    </header>
  )
}

