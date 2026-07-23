import { useState, useEffect } from 'react'
import { Users } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, BarChart, Bar, ReferenceLine,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency, formatNumber } from '@/lib/utils'
import { fetchRevenuePerStaff, fetchStaffRevenue } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface RevStaffProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

interface StoreRevStaff {
  store_id: number
  name: string
  code: string
  staff_count: number
  revenue: number
  orders: number
  revenue_per_staff: number
  orders_per_staff: number
}

interface RevStaffData {
  ok: boolean
  stores: StoreRevStaff[]
  chain_average: {
    revenue_per_staff: number
    total_staff: number
    total_revenue: number
  }
}

interface StaffItem {
  staff_id: string
  name: string
  code: string
  revenue: number
  orders: number
  active_days: number
  revenue_per_day: number
}

interface StaffRevenueData {
  ok: boolean
  staff: StaffItem[]
  summary: {
    total_revenue: number
    total_orders: number
    staff_count: number
    avg_revenue_per_staff: number
  }
}

type ViewMode = 'store' | 'staff'

export function RevenuePerStaff({ filters, onDrillDown }: RevStaffProps) {
  const [storeData, setStoreData] = useState<RevStaffData | null>(null)
  const [staffData, setStaffData] = useState<StaffRevenueData | null>(null)
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<ViewMode>('staff')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchRevenuePerStaff(filters),
      fetchStaffRevenue(filters),
    ])
      .then(([store, staff]) => {
        setStoreData(store as RevStaffData)
        setStaffData(staff as StaffRevenueData)
      })
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

  if (!storeData && !staffData) {
    return (
      <div className="text-center py-20 text-slate-500">
        <Users size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu hiệu suất nhân sự</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Doanh thu / Nhân viên</h1>
          <p className="text-sm text-slate-500 mt-1">
            {viewMode === 'staff' ? 'Chi tiết theo từng nhân viên' : 'Hiệu suất theo cửa hàng'}
          </p>
        </div>
        <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
          <button
            onClick={() => setViewMode('staff')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${viewMode === 'staff' ? 'bg-white shadow text-slate-900 font-medium' : 'text-slate-600 hover:text-slate-900'}`}
          >
            Nhân viên
          </button>
          <button
            onClick={() => setViewMode('store')}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${viewMode === 'store' ? 'bg-white shadow text-slate-900 font-medium' : 'text-slate-600 hover:text-slate-900'}`}
          >
            Cửa hàng
          </button>
        </div>
      </div>

      {viewMode === 'staff' && staffData && (
        <>
          {/* Staff Revenue Chart */}
          <Card>
            <CardHeader>
              <CardTitle>DT theo nhân viên</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={staffData.staff.slice(0, 10)} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                    <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={140} />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(value) => [formatCurrency(Number(value)), 'Doanh thu']}
                    />
                    <ReferenceLine x={staffData.summary.avg_revenue_per_staff} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'TB', fontSize: 10, fill: '#f59e0b' }} />
                    <Bar dataKey="revenue" fill="#8b5cf6" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Staff Detail Table */}
          <Card>
            <CardHeader>
              <CardTitle>Danh sách nhân viên</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="py-2.5 px-3 text-left font-medium text-slate-600">Nhân viên</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn hàng</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">Ngày hoạt động</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">DT/Ngày</th>
                    </tr>
                  </thead>
                  <tbody>
                    {staffData.staff.map((s) => (
                      <tr
                        key={s.staff_id}
                        className="border-b border-slate-100 hover:bg-slate-50 transition-colors cursor-pointer"
                        onClick={() => onDrillDown({ metricKey: 'staff_orders', clickedValue: s.staff_id })}
                        title="Nhấp để xem danh sách khách hàng phục vụ"
                      >
                        <td className="py-2.5 px-3 font-medium text-slate-900">{s.name}</td>
                        <td className="py-2.5 px-3 text-right text-slate-900">{formatCurrency(s.revenue)}</td>
                        <td className="py-2.5 px-3 text-right text-slate-700">{s.orders}</td>
                        <td className="py-2.5 px-3 text-right text-slate-700">{s.active_days}</td>
                        <td className={`py-2.5 px-3 text-right font-semibold ${s.revenue_per_day >= staffData.summary.avg_revenue_per_staff / 30 ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {formatCurrency(s.revenue_per_day)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>

          {/* Staff Summary */}
          <Card>
            <CardContent className="py-4">
              <div className="flex items-center justify-center gap-8 text-center">
                <div>
                  <p className="text-2xl font-bold text-slate-900">{staffData.summary.staff_count}</p>
                  <p className="text-xs text-slate-500">NV có doanh thu</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-slate-900">{formatCurrency(staffData.summary.total_revenue)}</p>
                  <p className="text-xs text-slate-500">Tổng doanh thu</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-purple-600">{formatCurrency(staffData.summary.avg_revenue_per_staff)}</p>
                  <p className="text-xs text-slate-500">TB/Nhân viên</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {viewMode === 'store' && storeData && storeData.stores.length > 0 && (
        <>
          {/* Store Revenue per Staff Bar Chart */}
          <Card>
            <CardHeader>
              <CardTitle>DT/Nhân viên theo cửa hàng</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[250px]">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={storeData.stores} layout="vertical" margin={{ left: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={(v: number) => formatCurrency(v)} />
                    <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={140} />
                    <Tooltip
                      contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                      formatter={(value) => [formatCurrency(Number(value)) + ' VND/NV', 'DT/Nhân viên']}
                    />
                    <ReferenceLine x={storeData.chain_average.revenue_per_staff} stroke="#f59e0b" strokeDasharray="3 3" label={{ value: 'TB chuỗi', fontSize: 10, fill: '#f59e0b' }} />
                    <Bar
                      dataKey="revenue_per_staff" fill="#8b5cf6" radius={[0, 4, 4, 0]}
                      className="cursor-pointer"
                      onClick={(data) => {
                        const name = (data as unknown as { name?: string })?.name
                        if (name) onDrillDown({ metricKey: 'revenue_per_staff_store', clickedValue: name })
                      }}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Store Detail Table */}
          <Card>
            <CardHeader>
              <CardTitle>Chi tiết theo cửa hàng</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="py-2.5 px-3 text-left font-medium text-slate-600">Cửa hàng</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">NV</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">DT/NV</th>
                      <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đơn/NV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {storeData.stores.map((s) => (
                      <tr
                        key={s.store_id}
                        className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                        onClick={() => onDrillDown({ metricKey: 'revenue_per_staff_store', clickedValue: s.name })}
                      >
                        <td className="py-2.5 px-3 font-medium text-slate-900">{s.name}</td>
                        <td className="py-2.5 px-3 text-right text-slate-700">{s.staff_count}</td>
                        <td className="py-2.5 px-3 text-right">{formatCurrency(s.revenue)}</td>
                        <td className={`py-2.5 px-3 text-right font-semibold ${s.revenue_per_staff >= storeData.chain_average.revenue_per_staff ? 'text-emerald-600' : 'text-rose-600'}`}>
                          {formatCurrency(s.revenue_per_staff)}
                        </td>
                        <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(s.orders_per_staff)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
