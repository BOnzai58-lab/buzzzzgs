import { useEffect, useRef, useState } from 'react'

export interface LogLine { ts: string; level: string; message: string }

export function useScanLogs(scanId: string | null) {
  const [logs, setLogs] = useState<LogLine[]>([])
  const ws = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!scanId) return
    const token = localStorage.getItem('token') || ''
    ws.current = new WebSocket(`ws://localhost:8000/api/v1/ws/scans/${scanId}?token=${token}`)
    ws.current.onmessage = e => {
      try { setLogs(prev => [...prev, JSON.parse(e.data)]) } catch {}
    }
    return () => { ws.current?.close() }
  }, [scanId])

  return { logs, clear: () => setLogs([]) }
}

