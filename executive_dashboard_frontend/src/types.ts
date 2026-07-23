export type PageType =
  | 'executive'
  | 'sales'
  | 'inventory'
  | 'quality'
  | 'leaderboard'
  | 'csat'
  | 'revenue-staff'
  | 'order-list'
  | 'b2b'
  | 'conversation'

export type Role = 'ceo' | 'bod' | 'cfo' | 'om' | 'rsm' | 'sup' | 'store_manager'

export interface FilterParams {
  start: string
  end: string
  region_id?: string
  store_id?: string
  period?: 'day' | 'month' | 'quarter' | 'year'
}

export interface NavItem {
  id: PageType
  label: string
  icon: string
}

export interface DrillDownRequest {
  metricKey: string
  clickedValue?: string
  title?: string
}
