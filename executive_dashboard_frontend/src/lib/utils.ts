import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  const val = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (val >= 1_000_000_000) return `${sign}${(val / 1_000_000_000).toFixed(1)}B`
  if (val >= 1_000_000) return `${sign}${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `${sign}${(val / 1_000).toFixed(1)}K`
  return sign + val.toLocaleString('vi-VN')
}

export function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`
}

export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null || isNaN(value)) return '0'
  return value.toLocaleString('vi-VN')
}

