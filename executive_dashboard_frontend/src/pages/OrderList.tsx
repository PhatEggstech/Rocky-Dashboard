import { useState, useEffect } from 'react'
import { ClipboardList } from 'lucide-react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { formatCurrency } from '@/lib/utils'
import { fetchOrderList } from '@/lib/api'
import type { FilterParams } from '@/types'

interface OrderListProps {
  filters: FilterParams
}

interface OrderItem {
  order_id: string
  store_id: string
  staff_id: string
  staff_name: string
  customer_name: string
  total_amount: number
  paid_amount: number
  payment_method: string
  status: string
  complete_at: string
  issue_at: string
}

interface OrderListData {
  ok: boolean
  orders: OrderItem[]
  total: number
}

export function OrderList({ filters }: OrderListProps) {
  const [data, setData] = useState<OrderListData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchOrderList(filters)
      .then((d) => setData(d as OrderListData))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="h-[400px] bg-slate-200 rounded-2xl" />
      </div>
    )
  }

  if (!data || data.orders.length === 0) {
    return (
      <div className="text-center py-20 text-slate-500">
        <ClipboardList size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có đơn hàng trong khoảng thời gian này</p>
      </div>
    )
  }

  const statusColor = (s: string) => {
    if (s === 'completed') return 'bg-emerald-100 text-emerald-700'
    if (s === 'cancelled') return 'bg-rose-100 text-rose-700'
    return 'bg-amber-100 text-amber-700'
  }

  const statusLabel = (s: string) => {
    if (s === 'completed') return 'Hoàn thành'
    if (s === 'cancelled') return 'Đã hủy'
    return 'Đang xử lý'
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Danh sách đơn hàng</h1>
        <p className="text-sm text-slate-500 mt-1">
          {data.total} đơn hàng trong kỳ
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Đơn hàng gần nhất</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Thời gian</th>
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Nhân viên</th>
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Khách hàng</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Tổng tiền</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Đã thu</th>
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Thanh toán</th>
                  <th className="py-2.5 px-3 text-center font-medium text-slate-600">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {data.orders.map((o) => (
                  <tr key={o.order_id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                    <td className="py-2.5 px-3 text-slate-700 whitespace-nowrap">
                      {o.complete_at ? o.complete_at.slice(0, 16).replace('T', ' ') : '-'}
                    </td>
                    <td className="py-2.5 px-3 text-slate-900 font-medium">{o.staff_name || '—'}</td>
                    <td className="py-2.5 px-3 text-slate-700">{o.customer_name || '—'}</td>
                    <td className="py-2.5 px-3 text-right text-slate-900">{formatCurrency(o.total_amount)}</td>
                    <td className="py-2.5 px-3 text-right text-emerald-600 font-medium">{formatCurrency(o.paid_amount)}</td>
                    <td className="py-2.5 px-3 text-slate-700">{o.payment_method}</td>
                    <td className="py-2.5 px-3 text-center">
                      <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${statusColor(o.status)}`}>
                        {statusLabel(o.status)}
                      </span>
                    </td>
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
