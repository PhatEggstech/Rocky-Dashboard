import type { ReactNode } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface KpiCardProps {
  label: string
  value: string
  trend?: number
  trendLabel?: string
  icon: ReactNode
  className?: string
}

export function KpiCard({ label, value, trend, trendLabel, icon, className }: KpiCardProps) {
  const isPositive = trend !== undefined && trend >= 0

  return (
    <div className={cn('bg-white rounded-2xl border border-slate-200 shadow-sm p-6', className)}>
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2.5 bg-blue-50 text-blue-600 rounded-xl">
          {icon}
        </div>
        <span className="text-sm font-medium text-slate-600">{label}</span>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {trend !== undefined && (
        <div className="flex items-center gap-1 mt-2">
          {isPositive ? (
            <TrendingUp size={14} className="text-emerald-600" />
          ) : (
            <TrendingDown size={14} className="text-rose-600" />
          )}
          <span className={cn(
            'text-xs font-semibold',
            isPositive ? 'text-emerald-600' : 'text-rose-600'
          )}>
            {isPositive ? '+' : ''}{trend.toFixed(1)}%
          </span>
          {trendLabel && (
            <span className="text-xs text-slate-400">{trendLabel}</span>
          )}
        </div>
      )}
    </div>
  )
}
