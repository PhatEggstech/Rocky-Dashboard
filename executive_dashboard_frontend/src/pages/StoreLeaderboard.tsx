import { useState, useEffect } from 'react'
import { Trophy } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchStoreLeaderboard } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface LeaderboardProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

interface StoreEntry {
  rank: number
  store_id: number
  name: string
  code: string
  revenue: number
  orders: number
  gross_profit: number
  customers: number
  growth_pct: number
  revenue_per_staff: number
  staff_count: number
}

interface LeaderboardData {
  ok: boolean
  leaderboard: StoreEntry[]
  metadata: { period: { start: string; end: string } }
}

export function StoreLeaderboard({ filters, onDrillDown }: LeaderboardProps) {
  const [data, setData] = useState<LeaderboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchStoreLeaderboard(filters)
      .then((d) => setData(d as LeaderboardData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="h-[300px] bg-slate-200 rounded-2xl" />
        <div className="h-[400px] bg-slate-200 rounded-2xl" />
      </div>
    )
  }

  if (!data || data.leaderboard.length === 0) {
    return (
      <div className="text-center py-20 text-slate-500">
        <Trophy size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu xếp hạng</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Xếp hạng cửa hàng</h1>
        <p className="text-sm text-slate-500 mt-1">So sánh hiệu suất giữa các cửa hàng</p>
      </div>

      {/* Revenue Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Doanh thu theo cửa hàng</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.leaderboard} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={140} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                />
                <Bar
                  dataKey="revenue" fill="#3b82f6" radius={[0, 4, 4, 0]}
                  className="cursor-pointer"
                  onClick={(data) => {
                    const name = (data as unknown as { name?: string })?.name
                    if (name) onDrillDown({ metricKey: 'leaderboard_store', clickedValue: name })
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Leaderboard Table */}
      <Card>
        <CardHeader>
          <CardTitle>Bảng xếp hạng chi tiết</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">#</th>
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Cửa hàng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Tăng trưởng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">DT/NV</th>
                </tr>
              </thead>
              <tbody>
                {data.leaderboard.map((s) => (
                  <tr
                    key={s.store_id}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => onDrillDown({ metricKey: 'leaderboard_store', clickedValue: s.name })}
                  >
                    <td className="py-2.5 px-3 font-bold text-slate-500">{s.rank}</td>
                    <td className="py-2.5 px-3 font-medium text-slate-900">{s.name}</td>
                    <td className="py-2.5 px-3 text-right">{formatCurrency(s.revenue)}</td>
                    <td className="py-2.5 px-3 text-right">{formatNumber(s.orders)}</td>
                    <td className={`py-2.5 px-3 text-right font-medium ${s.growth_pct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`}>
                      {s.growth_pct >= 0 ? '+' : ''}{s.growth_pct.toFixed(1)}%
                    </td>
                    <td className="py-2.5 px-3 text-right">{formatCurrency(s.revenue_per_staff)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
