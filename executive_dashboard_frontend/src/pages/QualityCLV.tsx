import { useState, useEffect } from 'react'
import { Star } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend,
  LineChart, Line,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchQuality } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface QualityProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

interface ReturnTrendItem {
  month: string
  return_count: number
  return_amount: number
  order_count: number
  return_rate_pct: number
}

interface RfmSegment {
  segment: string
  count: number
  total_monetary: number
}

interface TopCustomer {
  name: string
  monetary: number
  frequency: number
  recency_days: number
  segment: string
}

interface QualityData {
  ok: boolean
  returns_trend: ReturnTrendItem[]
  rfm_segments: RfmSegment[]
  top_customers: TopCustomer[]
}

export function QualityCLV({ filters, onDrillDown }: QualityProps) {
  const [data, setData] = useState<QualityData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchQuality(filters)
      .then((d) => setData(d as QualityData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="h-[300px] bg-slate-200 rounded-2xl" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-[280px] bg-slate-200 rounded-2xl" />
          <div className="h-[280px] bg-slate-200 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-20 text-slate-500">
        <Star size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu cho khoảng thời gian đã chọn</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Chất lượng & CLV</h1>
        <p className="text-sm text-slate-500 mt-1">Tỷ lệ trả hàng, RFM, Customer Lifetime Value</p>
      </div>

      {/* Return Rate Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Xu hướng tỷ lệ trả hàng</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.returns_trend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => `${v}%`} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [`${Number(value).toFixed(2)}%`, 'Tỷ lệ trả']}
                />
                <Line
                  type="monotone" dataKey="return_rate_pct" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }}
                  className="cursor-pointer"
                  activeDot={{
                    r: 6,
                    className: 'cursor-pointer',
                    onClick: (_, e) => {
                      const month = (e as unknown as { payload?: { month?: string } })?.payload?.month
                      if (month) onDrillDown({ metricKey: 'return_rate', clickedValue: month })
                    },
                  }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* RFM Segments + Top Customers */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RFM Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Phân khúc RFM</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.rfm_segments}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={90}
                    paddingAngle={3} dataKey="count" nameKey="segment"
                    className="cursor-pointer"
                    onClick={(_data, index) => {
                      const seg = data.rfm_segments[index]
                      if (seg) onDrillDown({ metricKey: 'rfm_segment', clickedValue: seg.segment })
                    }}
                  >
                    {data.rfm_segments.map((_, i) => (
                      <Cell key={`rfm-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatNumber(Number(value)), 'Khách']}
                  />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Top Customers Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top khách hàng giá trị cao</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="py-2 px-2 text-left font-medium text-slate-600">Tên</th>
                    <th className="py-2 px-2 text-right font-medium text-slate-600">Giá trị</th>
                    <th className="py-2 px-2 text-right font-medium text-slate-600">Đơn</th>
                    <th className="py-2 px-2 text-left font-medium text-slate-600">Nhóm</th>
                  </tr>
                </thead>
                <tbody>
                  {data.top_customers.map((c, i) => (
                    <tr key={i} className="border-b border-slate-100 hover:bg-slate-50">
                      <td className="py-2 px-2 text-slate-900">{c.name || 'N/A'}</td>
                      <td className="py-2 px-2 text-right text-slate-700">{formatCurrency(c.monetary)}</td>
                      <td className="py-2 px-2 text-right text-slate-700">{c.frequency}</td>
                      <td className="py-2 px-2">
                        <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-700">{c.segment}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* RFM Revenue Bar */}
      <Card>
        <CardHeader>
          <CardTitle>Doanh thu theo phân khúc RFM</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.rfm_segments} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="segment" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={100} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                />
                <Bar
                  dataKey="total_monetary" fill="#8b5cf6" radius={[0, 4, 4, 0]}
                  className="cursor-pointer"
                  onClick={(data) => {
                    const segment = (data as unknown as { segment?: string })?.segment
                    if (segment) onDrillDown({ metricKey: 'rfm_segment', clickedValue: segment })
                  }}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
