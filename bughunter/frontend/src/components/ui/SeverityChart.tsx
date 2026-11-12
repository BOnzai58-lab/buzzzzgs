import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS: Record<string, string> = { critical: '#ff3333', high: '#ff8800', medium: '#ffd700', low: '#3399ff', info: '#888888' }

export default function SeverityChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }))
  if (!chartData.length) return <p className="text-gray-600 text-sm text-center py-8">No findings yet</p>
  return (
    <ResponsiveContainer width="100%" height={200}>
      <PieChart>
        <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} paddingAngle={3} dataKey="value">
          {chartData.map((entry) => <Cell key={entry.name} fill={COLORS[entry.name] || '#888'} />)}
        </Pie>
        <Tooltip contentStyle={{ background: '#0d1225', border: '1px solid #1c2645', borderRadius: 8 }} itemStyle={{ color: '#ccc' }} />
        <Legend iconType="circle" iconSize={8} formatter={v => <span style={{ color: '#9ca3af', fontSize: 12 }}>{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  )
}

