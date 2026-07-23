import { useState, useEffect } from 'react'
import { SmilePlus } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatNumber } from '@/lib/utils'
import { fetchCsatByStore } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface CsatProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

interface CsatStoreEntry {
  store_id: number
  name: string
  code: string
  csat_score: number
  return_rate_pct: number
  total_orders: number
  total_returns: number
  data_source: string
}

interface CsatData {
  ok: boolean
  stores: CsatStoreEntry[]
  note: string
}

export function CsatByStore({ filters, onDrillDown }: CsatProps) {
  const [data, setData] = useState<CsatData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchCsatByStore(filters)
      .then((d) => setData(d as CsatData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="h-[300px] bg-slate-200 rounded-2xl" />
      </div>
    )
  }

  if (!data || data.stores.length === 0) {
    return (
      <div className="text-center py-20 text-slate-500">
        <SmilePlus size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu CSAT</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">CSAT theo cửa hàng</h1>
        <p className="text-sm text-slate-500 mt-1">
          Điểm hài lòng khách hàng
          <span className="ml-2 text-xs px-2 py-0.5 rounded bg-amber-50 text-amber-700">
            {data.stores[0]?.data_source === 'proxy_from_returns' ? 'Proxy từ tỷ lệ trả' : 'Real ZNS'}
          </span>
        </p>
      </div>

      {/* CSAT Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle>CSAT Score theo cửa hàng</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.stores} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={140} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [`${Number(value).toFixed(1)}`, 'CSAT']}
                />
                <Bar
                  dataKey="csat_score" fill="#10b981" radius={[0, 4, 4, 0]}
                  className="cursor-pointer"
                  onClick={(data) => {
                    const name = (data as unknown as { name?: string })?.name
                    if (name) onDrillDown({ metricKey: 'csat_store', clickedValue: name })
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Detail Table */}
      <Card>
        <CardHeader>
          <CardTitle>Chi tiết CSAT & Trả hàng</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Cửa hàng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">CSAT</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Tỷ lệ trả %</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn trả</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Tổng đơn</th>
                </tr>
              </thead>
              <tbody>
                {data.stores.map((s) => (
                  <tr
                    key={s.store_id}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => onDrillDown({ metricKey: 'csat_store', clickedValue: s.name })}
                  >
                    <td className="py-2.5 px-3 font-medium text-slate-900">{s.name}</td>
                    <td className={`py-2.5 px-3 text-right font-semibold ${s.csat_score >= 80 ? 'text-emerald-600' : s.csat_score >= 60 ? 'text-amber-600' : 'text-rose-600'}`}>
                      {s.csat_score.toFixed(1)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{s.return_rate_pct.toFixed(2)}%</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(s.total_returns)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(s.total_orders)}</td>
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
