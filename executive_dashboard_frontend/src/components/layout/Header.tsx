import { Calendar, ChevronDown } from 'lucide-react'
import type { FilterParams } from '@/types'

interface HeaderProps {
  filters: FilterParams
  onFiltersChange: (filters: FilterParams) => void
}

export function Header({ filters, onFiltersChange }: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 bg-white border-b border-slate-200 px-6 py-3">
      <div className="flex flex-wrap items-center gap-4">
        {/* Date range */}
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          <Calendar size={16} className="text-slate-400" />
          <input
            type="date"
            value={filters.start}
            onChange={(e) => onFiltersChange({ ...filters, start: e.target.value })}
            className="bg-transparent text-sm text-slate-700 outline-none"
          />
          <span className="text-slate-400">—</span>
          <input
            type="date"
            value={filters.end}
            onChange={(e) => onFiltersChange({ ...filters, end: e.target.value })}
            className="bg-transparent text-sm text-slate-700 outline-none"
          />
        </div>

        {/* Period selector */}
        <div className="relative">
          <select
            value={filters.period ?? 'day'}
            onChange={(e) => onFiltersChange({ ...filters, period: e.target.value as FilterParams['period'] })}
            className="appearance-none bg-slate-50 border border-slate-200 rounded-lg px-3 py-2 pr-8 text-sm text-slate-700 outline-none cursor-pointer"
          >
            <option value="day">Theo ngày</option>
            <option value="month">Theo tháng</option>
            <option value="quarter">Theo quý</option>
            <option value="year">Theo năm</option>
          </select>
          <ChevronDown size={14} className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
        </div>
      </div>
    </header>
  )
}
