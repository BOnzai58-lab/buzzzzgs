import { useState } from 'react'
import { useAuth } from '../store/auth'
import { useNavigate } from 'react-router-dom'
import { Crosshair, Loader } from 'lucide-react'
import toast from 'react-hot-toast'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      toast.error('Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-dark-900 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-3"><Crosshair size={40} className="text-accent-500" /></div>
          <h1 className="text-2xl font-bold text-white">BugHunter AI</h1>
          <p className="text-gray-500 text-sm mt-1">AI-powered bug bounty platform</p>
        </div>
        <form onSubmit={submit} className="card space-y-4">
          <div><label className="label">Email</label><input type="email" className="input" value={email} onChange={e => setEmail(e.target.value)} required autoFocus /></div>
          <div><label className="label">Password</label><input type="password" className="input" value={password} onChange={e => setPassword(e.target.value)} required /></div>
          <button type="submit" disabled={loading} className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-60">
            {loading && <Loader size={14} className="animate-spin" />}Sign In
          </button>
        </form>
        <p className="text-center text-xs text-gray-600 mt-4">First run? The first registered user becomes admin.</p>
      </div>
    </div>
  )
}

