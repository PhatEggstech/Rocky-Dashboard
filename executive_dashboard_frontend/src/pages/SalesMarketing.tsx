import { useState, useEffect } from 'react'
import { ShoppingCart } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell, Legend,
  AreaChart, Area,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchSalesMarketing } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface SalesMarketingProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

interface SalesData {
  ok: boolean
  daily_trend: { date: string; revenue: number; orders: number; customers: number }[]
  payment_mix: { method: string; amount: number; count: number }[]
  monthly_trend: { month: string; revenue: number; orders: number }[]
  customer_mix: { new: number; returning: number }
}

export function SalesMarketing({ filters, onDrillDown }: SalesMarketingProps) {
  const [data, setData] = useState<SalesData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchSalesMarketing(filters)
      .then((d) => setData(d as SalesData))
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
        <ShoppingCart size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu cho khoảng thời gian đã chọn</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Bán hàng & Marketing</h1>
        <p className="text-sm text-slate-500 mt-1">Doanh thu, đơn hàng, kênh thanh toán & chiến dịch</p>
      </div>

      {/* Daily Revenue Trend */}
      <Card>
        <CardHeader>
          <CardTitle>Xu hướng doanh thu hàng ngày</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.daily_trend}>
                <defs>
                  <linearGradient id="salesGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: string) => v.slice(5)} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                  labelFormatter={(label) => `Ngày ${label}`}
                />
                <Area
                  type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2} fill="url(#salesGradient)"
                  className="cursor-pointer"
                  onClick={(e) => {
                    const date = (e as unknown as { date?: string })?.date
                      ?? (e as unknown as { payload?: { date?: string } })?.payload?.date
                    if (date) onDrillDown({ metricKey: 'revenue_trend_point', clickedValue: date })
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Payment Mix + Monthly Trend */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Payment Method Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Phương thức thanh toán</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.payment_mix}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={90}
                    paddingAngle={3} dataKey="amount" nameKey="method"
                    className="cursor-pointer"
                    onClick={(_data, index) => {
                      const item = data.payment_mix[index]
                      if (item) onDrillDown({ metricKey: 'payment_method', clickedValue: item.method })
                    }}
                  >
                    {data.payment_mix.map((_, i) => (
                      <Cell key={`pm-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatCurrency(Number(value)) + ' VND']}
                  />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Monthly Revenue Bar */}
        <Card>
          <CardHeader>
            <CardTitle>Doanh thu theo tháng</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.monthly_trend}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#e2e8f0" />
                  <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                  />
                  <Bar
                    dataKey="revenue" fill="#10b981" radius={[4, 4, 0, 0]}
                    className="cursor-pointer"
                    onClick={(data) => {
                      const month = (data as unknown as { month?: string })?.month
                      if (month) onDrillDown({ metricKey: 'monthly_revenue', clickedValue: month })
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Customer Mix Summary */}
      <Card>
        <CardContent className="py-4">
          <div className="flex items-center justify-center gap-8">
            <div
              className="text-center cursor-pointer hover:bg-slate-50 rounded-lg p-3 transition-colors"
              onClick={() => onDrillDown({ metricKey: 'customer_segment', clickedValue: 'Khách mới' })}
            >
              <p className="text-2xl font-bold text-blue-600">{formatNumber(data.customer_mix.new)}</p>
              <p className="text-xs text-slate-500">Khách mới</p>
            </div>
            <div
              className="text-center cursor-pointer hover:bg-slate-50 rounded-lg p-3 transition-colors"
              onClick={() => onDrillDown({ metricKey: 'customer_segment', clickedValue: 'Khách quay lại' })}
            >
              <p className="text-2xl font-bold text-emerald-600">{formatNumber(data.customer_mix.returning)}</p>
              <p className="text-xs text-slate-500">Khách quay lại</p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
