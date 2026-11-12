import { create } from 'zustand'
interface UIStore { sidebarOpen: boolean; toggleSidebar: () => void }
export const useUI = create<UIStore>(set => ({
  sidebarOpen: true,
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
}))

