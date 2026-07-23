import { useEffect, useCallback } from 'react'
import { X, Download } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatCurrency, formatNumber } from '@/lib/utils'

export interface DrillDownColumn {
  key: string
  label: string
  type: 'text' | 'currency' | 'number' | 'percent'
}

export interface DrillDownData {
  ok: boolean
  metric_key: string
  title: string
  subtitle: string
  columns: DrillDownColumn[]
  rows: Record<string, unknown>[]
  summary: Record<string, unknown>
}

interface DrillDownPanelProps {
  data: DrillDownData | null
  loading: boolean
  onClose: () => void
}

function formatCell(value: unknown, type: DrillDownColumn['type']): string {
  if (value === null || value === undefined) return '—'
  const num = Number(value)
  switch (type) {
    case 'currency':
      return formatCurrency(num)
    case 'number':
      return formatNumber(num)
    case 'percent':
      return `${num}%`
    case 'text':
    default:
      return String(value)
  }
}

function exportCsv(data: DrillDownData) {
  const header = data.columns.map((c) => c.label).join(',')
  const rows = data.rows.map((row) =>
    data.columns
      .map((col) => {
        const val = row[col.key]
        if (typeof val === 'string' && val.includes(',')) return `"${val}"`
        return val ?? ''
      })
      .join(',')
  )
  const csv = [header, ...rows].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${data.metric_key}_detail.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export function DrillDownPanel({ data, loading, onClose }: DrillDownPanelProps) {
  const isOpen = loading || data !== null

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    },
    [onClose]
  )

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [isOpen, handleKeyDown])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/20 z-40 transition-opacity"
        onClick={onClose}
      />

      {/* Panel */}
      <div
        className={cn(
          'fixed top-0 right-0 h-full z-50 bg-white shadow-2xl',
          'w-full md:w-[480px] lg:w-[520px]',
          'flex flex-col',
          'animate-in slide-in-from-right duration-300'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div className="min-w-0 flex-1">
            {loading ? (
              <div className="space-y-2">
                <div className="h-5 bg-slate-200 rounded w-48 animate-pulse" />
                <div className="h-3 bg-slate-100 rounded w-32 animate-pulse" />
              </div>
            ) : data ? (
              <>
                <h2 className="text-lg font-semibold text-slate-900 truncate">
                  {data.title}
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">{data.subtitle}</p>
              </>
            ) : null}
          </div>
          <div className="flex items-center gap-2 ml-3">
            {data && data.rows.length > 0 && (
              <button
                onClick={() => exportCsv(data)}
                className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
                title="Xuất CSV"
              >
                <Download size={16} />
              </button>
            )}
            <button
              onClick={onClose}
              className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <div className="space-y-3">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-10 bg-slate-100 rounded animate-pulse" />
              ))}
            </div>
          ) : data && data.rows.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              Không có dữ liệu chi tiết
            </div>
          ) : data ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200">
                    {data.columns.map((col) => (
                      <th
                        key={col.key}
                        className={cn(
                          'py-2.5 px-3 font-medium text-slate-600 whitespace-nowrap',
                          col.type === 'text' ? 'text-left' : 'text-right'
                        )}
                      >
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.rows.map((row, idx) => (
                    <tr
                      key={idx}
                      className="border-b border-slate-100 hover:bg-slate-50 transition-colors"
                    >
                      {data.columns.map((col) => (
                        <td
                          key={col.key}
                          className={cn(
                            'py-2.5 px-3 whitespace-nowrap',
                            col.type === 'text' ? 'text-left text-slate-900' : 'text-right text-slate-700'
                          )}
                        >
                          {formatCell(row[col.key], col.type)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>

        {/* Footer summary */}
        {data && Object.keys(data.summary).length > 0 && (
          <div className="border-t border-slate-200 px-4 py-3 bg-slate-50">
            <div className="flex flex-wrap gap-4 text-xs text-slate-600">
              {Object.entries(data.summary).map(([key, val]) => (
                <span key={key}>
                  <span className="font-medium">{key.replace(/_/g, ' ')}:</span>{' '}
                  {typeof val === 'number' ? formatNumber(val) : String(val)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
