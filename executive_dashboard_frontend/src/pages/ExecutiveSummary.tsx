import { useState, useEffect } from 'react'
import {
  DollarSign,
  ShoppingCart,
  TrendingUp,
  Users,
  Percent,
  Package,
} from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  BarChart, Bar, AreaChart, Area,
} from 'recharts'
import { KpiCard } from '@/components/ui/KpiCard'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchExecutiveSummary } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface ExecutiveSummaryProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

interface Scorecards {
  revenue: number
  subtotal: number
  orders: number
  aov: number
  gpm_pct: number | null
  unique_customers: number
  revenue_growth_pct: number
  gross_profit: number
}

interface TrendPoint {
  date: string
  revenue: number
  orders: number
}

interface ProductItem {
  name: string
  revenue: number
  units_sold: number
}

interface DashboardData {
  ok: boolean
  scorecards: Scorecards
  charts: {
    revenue_trend: TrendPoint[]
    top_products: ProductItem[]
    customer_segments: {
      new_customers: number
      returning_customers: number
    }
  }
  metadata: {
    period: { start: string; end: string }
    stores_count: number
  }
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

export function ExecutiveSummary({ filters, onDrillDown }: ExecutiveSummaryProps) {
  const [data, setData] = useState<DashboardData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchExecutiveSummary(filters)
      .then((d) => setData(d as DashboardData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="h-32 bg-slate-200 rounded-2xl" />
          ))}
        </div>
        <div className="h-[300px] bg-slate-200 rounded-2xl" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-20 text-slate-500">
        Không có dữ liệu cho khoảng thời gian đã chọn
      </div>
    )
  }

  const { scorecards: sc, charts } = data

  // Prepare customer segment data for pie chart
  const segmentData = [
    { name: 'Khách mới', value: charts.customer_segments.new_customers },
    { name: 'Khách quay lại', value: charts.customer_segments.returning_customers },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Tổng quan điều hành</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.metadata.stores_count} cửa hàng | {data.metadata.period.start} — {data.metadata.period.end}
        </p>
      </div>

      {/* Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7 gap-4">
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'revenue' })}>
          <KpiCard
            label="Doanh thu"
            value={formatCurrency(sc.revenue)}
            trend={sc.revenue_growth_pct}
            trendLabel="vs kỳ trước"
            icon={<DollarSign size={20} />}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'subtotal' })}>
          <KpiCard
            label="Doanh số"
            value={formatCurrency(sc.subtotal)}
            icon={<TrendingUp size={20} />}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'orders' })}>
          <KpiCard
            label="Đơn hàng"
            value={formatNumber(sc.orders)}
            icon={<ShoppingCart size={20} />}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'aov' })}>
          <KpiCard
            label="AOV"
            value={formatCurrency(sc.aov)}
            icon={<TrendingUp size={20} />}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'gpm' })}>
          <KpiCard
            label="Biên LN gộp"
            value={sc.gpm_pct !== null && sc.gpm_pct !== undefined ? `${sc.gpm_pct}%` : 'N/A'}
            icon={<Percent size={20} />}
            trendLabel={sc.gpm_pct === null ? 'Chưa có dữ liệu giá vốn' : undefined}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'customers' })}>
          <KpiCard
            label="Khách hàng"
            value={formatNumber(sc.unique_customers)}
            icon={<Users size={20} />}
          />
        </div>
        <div className="cursor-pointer hover:ring-2 hover:ring-blue-200 rounded-2xl transition-all" onClick={() => onDrillDown({ metricKey: 'gross_profit' })}>
          <KpiCard
            label="Lợi nhuận gộp"
            value={formatCurrency(sc.gross_profit)}
            icon={<Package size={20} />}
          />
        </div>
      </div>

      {/* Revenue Trend Chart */}
      <Card>
        <CardHeader>
          <CardTitle>Xu hướng doanh thu</CardTitle>
          <p className="text-xs text-slate-500 mt-1">Doanh thu theo ngày trong kỳ</p>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={charts.revenue_trend}>
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(v: string) => v.slice(5)}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: '#64748b' }}
                  tickFormatter={(v: number) => formatCurrency(v)}
                />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                  labelFormatter={(label) => `Ngày ${label}`}
                />
                <Area
                  type="monotone"
                  dataKey="revenue"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  fill="url(#revenueGradient)"
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

      {/* Bottom row: Top Products + Customer Segments */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Products */}
        <Card>
          <CardHeader>
            <CardTitle>Top sản phẩm</CardTitle>
            <p className="text-xs text-slate-500 mt-1">10 sản phẩm doanh thu cao nhất</p>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={charts.top_products} layout="vertical" margin={{ left: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis
                    type="number"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(v: number) => formatCurrency(v)}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    width={120}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                  />
                  <Bar
                    dataKey="revenue"
                    fill="#3b82f6"
                    radius={[0, 4, 4, 0]}
                    className="cursor-pointer"
                    onClick={(data) => {
                      const name = (data as unknown as { name?: string })?.name
                      if (name) onDrillDown({ metricKey: 'top_product', clickedValue: name })
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Customer Segments */}
        <Card>
          <CardHeader>
            <CardTitle>Phân khúc khách hàng</CardTitle>
            <p className="text-xs text-slate-500 mt-1">Khách mới vs khách quay lại</p>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={segmentData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                    className="cursor-pointer"
                    onClick={(_data, index) => {
                      const seg = segmentData[index]
                      if (seg) onDrillDown({ metricKey: 'customer_segment', clickedValue: seg.name })
                    }}
                  >
                    {segmentData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatNumber(Number(value)), 'Khách']}
                  />
                  <Legend
                    verticalAlign="bottom"
                    height={36}
                    formatter={(value: string) => <span className="text-sm text-slate-600">{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
