import { useEffect, useRef } from 'react'
import type { LogLine } from '../../lib/websocket'

const levelColor: Record<string, string> = { INFO: 'text-gray-300', WARN: 'text-warn-400', ERROR: 'text-danger-400', DEBUG: 'text-gray-500' }

export default function ScanLogViewer({ logs }: { logs: LogLine[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => { ref.current?.scrollTo(0, ref.current.scrollHeight) }, [logs])
  return (
    <div ref={ref} className="bg-dark-900 border border-dark-600 rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs">
      {logs.length === 0 ? (
        <p className="text-gray-600">Waiting for scan logs...</p>
      ) : logs.map((l, i) => (
        <div key={i} className="mb-0.5">
          <span className="text-gray-600">{new Date(l.ts).toLocaleTimeString()} </span>
          <span className={`font-bold ${levelColor[l.level] || 'text-gray-300'}`}>[{l.level}] </span>
          <span className="text-gray-300">{l.message}</span>
        </div>
      ))}
    </div>
  )
}

