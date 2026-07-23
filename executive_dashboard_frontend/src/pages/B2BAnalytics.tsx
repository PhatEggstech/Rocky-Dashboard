import { useState, useEffect } from 'react'
import { Building2 } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchB2B } from '@/lib/api'
import type { FilterParams } from '@/types'

interface B2BData {
  ok: boolean
  debt_summary: {
    total_customers_with_debt: number
    total_debt: number
    total_revenue: number
    total_orders: number
    total_left_amount: number
  }
  top_debtors: { customer_id: string; name: string; debt_amount: number; need_pay: number; total_orders: number; last_transaction_at: string; left_amount: number; payment_state: number }[]
  top_customers: { customer_id: string; name: string; total_revenue: number; total_orders: number; last_transaction_at: string }[]
}

function getDefaultFilters(): FilterParams {
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth() - 6, 1)
  return {
    start: start.toISOString().slice(0, 10),
    end: today.toISOString().slice(0, 10),
    period: 'month',
  }
}

interface B2BAnalyticsProps {
  onDrillDown?: (req: { metricKey: string; clickedValue?: string }) => void
}

export function B2BAnalytics({ onDrillDown }: B2BAnalyticsProps) {
  const [data, setData] = useState<B2BData | null>(null)
  const [loading, setLoading] = useState(true)
  const [filters] = useState<FilterParams>(getDefaultFilters)

  useEffect(() => {
    setLoading(true)
    fetchB2B(filters)
      .then((d) => setData(d as B2BData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-slate-200 rounded-2xl" />
          ))}
        </div>
        <div className="h-[300px] bg-slate-200 rounded-2xl" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-20 text-slate-500">
        <Building2 size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu B2B</p>
      </div>
    )
  }

  const { debt_summary: ds } = data
  const avgDebt = ds.total_customers_with_debt > 0 ? ds.total_debt / ds.total_customers_with_debt : 0

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">B2B Analytics</h1>
        <p className="text-sm text-slate-500 mt-1">Doanh thu đại lý, công nợ, quản lý kênh phân phối</p>
      </div>

      {/* Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Tổng đại lý</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatNumber(ds.total_customers_with_debt)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Tổng công nợ</p>
            <p className="text-2xl font-bold text-rose-600 mt-1">{formatCurrency(ds.total_debt)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Còn phải trả</p>
            <p className="text-2xl font-bold text-orange-600 mt-1">{formatCurrency(ds.total_left_amount)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Tổng doanh thu</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(ds.total_revenue)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">TB nợ/đại lý</p>
            <p className="text-2xl font-bold text-amber-600 mt-1">{formatCurrency(avgDebt)}</p>
          </CardContent>
        </Card>
      </div>

      {/* Top Debtors Bar */}
      <Card>
        <CardHeader>
          <CardTitle>Top công nợ đại lý</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.top_debtors.slice(0, 10)} layout="vertical" margin={{ left: 30 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={150} />
                <Tooltip
                  contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Công nợ']}
                />
                <Bar dataKey="debt_amount" fill="#ef4444" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Debtor Table */}
      <Card>
        <CardHeader>
          <CardTitle>Chi tiết công nợ đại lý</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Đại lý</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Công nợ</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn hàng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">GD cuối</th>
                </tr>
              </thead>
              <tbody>
                {data.top_debtors.map((d) => (
                  <tr
                    key={d.customer_id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onDrillDown?.({ metricKey: 'b2b_customer_orders', clickedValue: d.customer_id })}
                    title="Nhấp để xem danh sách đơn hàng"
                  >
                    <td className="py-2.5 px-3 font-medium text-slate-900">{d.name}</td>
                    <td className={`py-2.5 px-3 text-right font-semibold ${d.debt_amount > 50_000_000 ? 'text-rose-600' : d.debt_amount > 20_000_000 ? 'text-amber-600' : 'text-emerald-600'}`}>
                      {formatCurrency(d.debt_amount)}
                    </td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatCurrency(d.need_pay)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(d.total_orders)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-500 text-xs">{d.last_transaction_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Top Customers Table */}
      <Card>
        <CardHeader>
          <CardTitle>Top đại lý theo doanh thu</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Đại lý</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn hàng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">GD cuối</th>
                </tr>
              </thead>
              <tbody>
                {data.top_customers.map((c) => (
                  <tr
                    key={c.customer_id}
                    className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => onDrillDown?.({ metricKey: 'b2b_customer_orders', clickedValue: c.customer_id })}
                    title="Nhấp để xem danh sách đơn hàng"
                  >
                    <td className="py-2.5 px-3 font-medium text-slate-900">{c.name}</td>
                    <td className="py-2.5 px-3 text-right font-semibold text-slate-900">{formatCurrency(c.total_revenue)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(c.total_orders)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-500 text-xs">{c.last_transaction_at}</td>
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
