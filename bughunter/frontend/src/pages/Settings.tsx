import { useState } from 'react'
import { Shield, Info } from 'lucide-react'

const tabs = ['AI Config', 'Security', 'About']

export default function Settings() {
  const [tab, setTab] = useState('AI Config')
  const [aiUrl, setAiUrl] = useState('https://api.openai.com/v1')
  const [aiModel, setAiModel] = useState('gpt-4o-mini')

  return (
    <div className="p-6 max-w-2xl">
      <div className="flex gap-1 mb-6 border-b border-dark-600">
        {tabs.map(t => (
          <button key={t} onClick={() => setTab(t)} className={`px-4 py-2 text-sm transition-colors border-b-2 -mb-px ${tab === t ? 'border-accent-500 text-accent-500' : 'border-transparent text-gray-500 hover:text-gray-300'}`}>{t}</button>
        ))}
      </div>

      {tab === 'AI Config' && (
        <div className="space-y-4">
          <div className="card border-accent-500/30">
            <p className="text-xs text-accent-500 mb-3">⚡ Standalone Bug Bounty AI Engine (OpenAI-compatible)</p>
            <div className="space-y-3">
              <div><label className="label">AI Base URL</label><input className="input font-mono text-xs" value={aiUrl} onChange={e => setAiUrl(e.target.value)} placeholder="https://api.openai.com/v1" /></div>
              <div><label className="label">Model</label><input className="input font-mono text-xs" value={aiModel} onChange={e => setAiModel(e.target.value)} placeholder="gpt-4o-mini, claude-3-5-sonnet, etc." /></div>
            </div>
            <p className="text-xs text-gray-500 mt-3">Configure your provider API key in your backend <code className="text-gray-400">.env</code> file (e.g. OpenAI, OpenRouter, Groq, Ollama).</p>
          </div>

          <div className="card bg-dark-700/50">
            <h3 className="text-sm font-semibold text-gray-300 mb-2">Supported Direct Providers</h3>
            {[
              'OpenAI: https://api.openai.com/v1 (gpt-4o, gpt-4o-mini)',
              'OpenRouter: https://openrouter.ai/api/v1',
              'Groq: https://api.groq.com/openai/v1 (llama-3.3-70b-versatile)',
              'Local Ollama: http://localhost:11434/v1 (qwen2.5-coder, llama3)',
            ].map(m => (
              <p key={m} className="text-xs font-mono text-gray-400 mb-1.5">• {m}</p>
            ))}
          </div>
        </div>
      )}

      {tab === 'Security' && (
        <div className="card space-y-3">
          <div className="flex items-center gap-2 text-warn-400"><Shield size={16} /><span className="text-sm font-semibold">Security Settings</span></div>
          <div><label className="label">New Password</label><input type="password" className="input" placeholder="••••••••" /></div>
          <div><label className="label">Confirm Password</label><input type="password" className="input" placeholder="••••••••" /></div>
          <button className="btn-primary">Update Password</button>
          <div className="pt-4 border-t border-dark-600">
            <p className="text-xs text-gray-500">API keys are stored encrypted in the backend. Never share your .env file.</p>
          </div>
        </div>
      )}

      {tab === 'About' && (
        <div className="card space-y-4">
          <div className="flex items-center gap-3">
            <div className="bg-accent-500/10 p-3 rounded-lg"><Info size={20} className="text-accent-500" /></div>
            <div><p className="font-bold text-white">BugHunter AI</p><p className="text-xs text-gray-500">Version 1.0.0</p></div>
          </div>
          <div className="space-y-2 text-xs text-gray-500">
            <p>Autonomous AI-powered bug bounty reconnaissance and vulnerability analysis platform.</p>
            <p>Built with FastAPI · React · PostgreSQL · Redis · Celery</p>
            <div className="pt-2 border-t border-dark-600">
              <p className="text-warn-400">⚠️ Only scan authorized targets within program scope.</p>
              <p className="mt-1">Backend API: <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer" className="text-accent-500 hover:underline">http://localhost:8000/docs</a></p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

