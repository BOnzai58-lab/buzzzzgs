import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { login as apiLogin, getMe } from '../lib/api'

interface User { id: string; email: string; role: string }
interface AuthStore {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  loadUser: () => Promise<void>
  isAdmin: () => boolean
  isAnalyst: () => boolean
}

export const useAuth = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      login: async (email, password) => {
        const res = await apiLogin(email, password)
        const token = res.data.access_token
        localStorage.setItem('token', token)
        set({ token })
        const me = await getMe()
        set({ user: me.data })
      },
      logout: () => {
        localStorage.removeItem('token')
        set({ user: null, token: null })
      },
      loadUser: async () => {
        try { const me = await getMe(); set({ user: me.data }) } catch { get().logout() }
      },
      isAdmin: () => get().user?.role === 'admin',
      isAnalyst: () => ['admin', 'analyst'].includes(get().user?.role || ''),
    }),
    { name: 'auth-store', partialize: s => ({ token: s.token }) }
  )
)

