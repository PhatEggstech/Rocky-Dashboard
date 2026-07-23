import { useState, useEffect } from 'react'
import { Package, AlertTriangle, TrendingDown } from 'lucide-react'
import {
  XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
  BarChart, Bar,
} from 'recharts'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { cn, formatCurrency, formatNumber } from '@/lib/utils'
import { fetchInventory, fetchInventoryByCategory } from '@/lib/api'
import type { FilterParams, DrillDownRequest } from '@/types'

interface InventoryProps {
  filters: FilterParams
  onDrillDown: (req: DrillDownRequest) => void
}

const CHART_COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#06b6d4']

interface InventoryData {
  ok: boolean
  scorecards: {
    total_skus: number
    total_revenue: number
    total_units: number
    avg_price: number
    top_category: string
  }
  wms_scorecards?: {
    total_inventory_value: number
    stock_cover_days_avg: number
    dead_stock_pct: number
    oos_pct: number
  }
  category_mix: { category: string; revenue: number; units_sold: number }[]
  top_products: { name: string; category: string; revenue: number; units_sold: number; avg_price: number }[]
  bottom_products: { name: string; category: string; revenue: number; units_sold: number; avg_price: number }[]
  monthly_trend: { month: string; category: string; revenue: number }[]
}

interface CategoryItem {
  category: string
  sku_count: number
  total_on_hand: number
  total_value: number
  dead_stock_count: number
  avg_cover_days: number
}

interface CategoryData {
  ok: boolean
  categories: CategoryItem[]
  summary: { total_categories: number; total_skus: number; total_value: number }
}

export function InventorySupplyChain({ filters, onDrillDown }: InventoryProps) {
  const [data, setData] = useState<InventoryData | null>(null)
  const [categoryData, setCategoryData] = useState<CategoryData | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'revenue' | 'units'>('revenue')

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchInventory(filters),
      fetchInventoryByCategory(filters),
    ])
      .then(([inv, cat]) => {
        setData(inv as InventoryData)
        setCategoryData(cat as CategoryData)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [filters.start, filters.end, filters.region_id, filters.store_id])

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 bg-slate-200 rounded w-64" />
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-slate-200 rounded-2xl" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-[300px] bg-slate-200 rounded-2xl" />
          <div className="h-[300px] bg-slate-200 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center py-20 text-slate-500">
        <Package size={48} className="mx-auto text-slate-300 mb-4" />
        <p>Không có dữ liệu tồn kho cho khoảng thời gian đã chọn</p>
      </div>
    )
  }

  const { scorecards: sc } = data

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Tồn kho & Chuỗi cung ứng</h1>
        <p className="text-sm text-slate-500 mt-1">Phân tích danh mục, sản phẩm bán chạy & chậm</p>
      </div>

      {/* Scorecards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Tổng SKU</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatNumber(sc.total_skus)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Doanh thu SP</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(sc.total_revenue)}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Danh mục top</p>
            <p className="text-2xl font-bold text-blue-600 mt-1">{sc.top_category}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5 pb-4">
            <p className="text-sm text-slate-500">Giá trung bình</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(sc.avg_price)}</p>
          </CardContent>
        </Card>
      </div>

      {/* WMS Inventory Scorecards (conditional) */}
      {data.wms_scorecards && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-5 pb-4">
              <p className="text-sm text-slate-500">Giá trị tồn kho</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{formatCurrency(data.wms_scorecards.total_inventory_value)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <p className="text-sm text-slate-500">Ngày tồn kho TB</p>
              <p className="text-2xl font-bold text-slate-900 mt-1">{formatNumber(data.wms_scorecards.stock_cover_days_avg)}</p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-1.5">
                <p className="text-sm text-slate-500">Hàng chết</p>
                <AlertTriangle size={14} className="text-amber-500" />
              </div>
              <p className={`text-2xl font-bold mt-1 ${data.wms_scorecards.dead_stock_pct > 20 ? 'text-red-600' : data.wms_scorecards.dead_stock_pct > 10 ? 'text-amber-600' : 'text-green-600'}`}>
                {data.wms_scorecards.dead_stock_pct}%
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-5 pb-4">
              <div className="flex items-center gap-1.5">
                <p className="text-sm text-slate-500">Hết hàng (OOS)</p>
                <TrendingDown size={14} className="text-red-500" />
              </div>
              <p className={`text-2xl font-bold mt-1 ${data.wms_scorecards.oos_pct > 10 ? 'text-red-600' : data.wms_scorecards.oos_pct > 5 ? 'text-amber-600' : 'text-green-600'}`}>
                {data.wms_scorecards.oos_pct}%
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Category Pie + Top Products Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Mix Pie */}
        <Card>
          <CardHeader>
            <CardTitle>Doanh thu theo danh mục</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.category_mix}
                    cx="50%" cy="50%"
                    innerRadius={50} outerRadius={90}
                    paddingAngle={3} dataKey="revenue" nameKey="category"
                    className="cursor-pointer"
                    onClick={(_data, index) => {
                      const cat = data.category_mix[index]
                      if (cat) onDrillDown({ metricKey: 'inventory_category', clickedValue: cat.category })
                    }}
                  >
                    {data.category_mix.map((_, i) => (
                      <Cell key={`cat-${i}`} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [formatCurrency(Number(value)) + ' VND', 'Doanh thu']}
                  />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Top 10 Products Bar */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Sản phẩm bán chạy (Top 10)</CardTitle>
              <p className="text-xs text-slate-500 mt-1">
                Xếp hạng theo {sortBy === 'revenue' ? 'doanh thu' : 'số lượng bán'}
              </p>
            </div>
            <div className="flex gap-1 bg-slate-100 p-0.5 rounded-lg text-xs">
              <button
                onClick={() => setSortBy('revenue')}
                className={cn(
                  "px-2.5 py-1 rounded-md transition-colors",
                  sortBy === 'revenue' ? "bg-white shadow text-slate-900 font-medium" : "text-slate-600 hover:text-slate-900"
                )}
              >
                Doanh thu
              </button>
              <button
                onClick={() => setSortBy('units')}
                className={cn(
                  "px-2.5 py-1 rounded-md transition-colors",
                  sortBy === 'units' ? "bg-white shadow text-slate-900 font-medium" : "text-slate-600 hover:text-slate-900"
                )}
              >
                Số lượng
              </button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={[...data.top_products].sort((a, b) => 
                    sortBy === 'revenue' ? b.revenue - a.revenue : b.units_sold - a.units_sold
                  )}
                  layout="vertical"
                  margin={{ left: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                  <XAxis
                    type="number"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#64748b' }}
                    tickFormatter={(v: number) => sortBy === 'revenue' ? formatCurrency(v) : formatNumber(v)}
                  />
                  <YAxis type="category" dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} width={130} />
                  <Tooltip
                    contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    formatter={(value) => [
                      sortBy === 'revenue' ? formatCurrency(Number(value)) + ' VND' : formatNumber(Number(value)) + ' SP',
                      sortBy === 'revenue' ? 'Doanh thu' : 'Số lượng bán'
                    ]}
                  />
                  <Bar
                    dataKey={sortBy === 'revenue' ? 'revenue' : 'units_sold'}
                    fill={sortBy === 'revenue' ? '#3b82f6' : '#10b981'}
                    radius={[0, 4, 4, 0]}
                    className="cursor-pointer"
                    onClick={(barData) => {
                      const name = (barData as unknown as { name?: string })?.name
                      if (name) onDrillDown({ metricKey: 'inventory_product', clickedValue: name })
                    }}
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom 10 Slow Movers Table */}
      <Card>
        <CardHeader>
          <CardTitle>Sản phẩm bán chậm (Bottom 10)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Sản phẩm</th>
                  <th className="py-2.5 px-3 text-left font-medium text-slate-600">Danh mục</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">SL bán</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Doanh thu</th>
                  <th className="py-2.5 px-3 text-right font-medium text-slate-600">Giá TB</th>
                </tr>
              </thead>
              <tbody>
                {data.bottom_products.map((p, i) => (
                  <tr
                    key={i}
                    className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                    onClick={() => onDrillDown({ metricKey: 'inventory_product', clickedValue: p.name })}
                  >
                    <td className="py-2.5 px-3 font-medium text-slate-900">{p.name}</td>
                    <td className="py-2.5 px-3 text-slate-600">{p.category}</td>
                    <td className="py-2.5 px-3 text-right font-semibold text-rose-600">{formatNumber(p.units_sold)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatCurrency(p.revenue)}</td>
                    <td className="py-2.5 px-3 text-right text-slate-700">{formatCurrency(p.avg_price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Inventory by Category (WMS) */}
      {categoryData && categoryData.categories.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Tồn kho theo nhóm sản phẩm</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    <th className="py-2.5 px-3 text-left font-medium text-slate-600">Nhóm SP</th>
                    <th className="py-2.5 px-3 text-right font-medium text-slate-600">SKU</th>
                    <th className="py-2.5 px-3 text-right font-medium text-slate-600">Tồn kho</th>
                    <th className="py-2.5 px-3 text-right font-medium text-slate-600">Giá trị</th>
                    <th className="py-2.5 px-3 text-right font-medium text-slate-600">Hàng chết</th>
                    <th className="py-2.5 px-3 text-right font-medium text-slate-600">Ngày tồn TB</th>
                  </tr>
                </thead>
                <tbody>
                  {categoryData.categories.map((c, i) => (
                    <tr
                      key={i}
                      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
                      onClick={() => onDrillDown({ metricKey: 'inventory_category', clickedValue: c.category })}
                    >
                      <td className="py-2.5 px-3 font-medium text-slate-900">{c.category}</td>
                      <td className="py-2.5 px-3 text-right text-slate-700">{c.sku_count}</td>
                      <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(c.total_on_hand)}</td>
                      <td className="py-2.5 px-3 text-right text-slate-900">{formatCurrency(c.total_value)}</td>
                      <td className={`py-2.5 px-3 text-right font-medium ${c.dead_stock_count > 0 ? 'text-rose-600' : 'text-emerald-600'}`}>{c.dead_stock_count}</td>
                      <td className="py-2.5 px-3 text-right text-slate-700">{formatNumber(c.avg_cover_days)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
