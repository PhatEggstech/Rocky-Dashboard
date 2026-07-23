import type { FilterParams, DrillDownRequest } from '@/types'

const API_BASE = '/api/react'

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('edp_token')
  const headers: HeadersInit = {}
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

export function logout() {
  localStorage.removeItem('edp_token')
  window.location.reload()
}

async function fetchJSON<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: authHeaders() })
  if (res.status === 401) {
    logout()
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json() as Promise<T>
}

function buildQueryString(params: FilterParams): string {
  const qs = new URLSearchParams({
    start: params.start,
    end: params.end,
  })
  if (params.region_id) qs.set('region_id', params.region_id)
  if (params.store_id) qs.set('store_id', params.store_id)
  if (params.period) qs.set('period', params.period)
  return qs.toString()
}

export async function fetchExecutiveSummary(params: FilterParams) {
  return fetchJSON(`${API_BASE}/executive-summary?${buildQueryString(params)}`)
}

export async function fetchSalesMarketing(params: FilterParams) {
  return fetchJSON(`${API_BASE}/sales-marketing?${buildQueryString(params)}`)
}

export async function fetchInventory(params: FilterParams) {
  return fetchJSON(`${API_BASE}/inventory?${buildQueryString(params)}`)
}

export async function fetchQuality(params: FilterParams) {
  return fetchJSON(`${API_BASE}/quality?${buildQueryString(params)}`)
}

export async function fetchStoreLeaderboard(params: FilterParams) {
  return fetchJSON(`${API_BASE}/store-leaderboard?${buildQueryString(params)}`)
}

export async function fetchCsatByStore(params: FilterParams) {
  return fetchJSON(`${API_BASE}/csat-by-store?${buildQueryString(params)}`)
}

export async function fetchRevenuePerStaff(params: FilterParams) {
  return fetchJSON(`${API_BASE}/revenue-per-staff?${buildQueryString(params)}`)
}

export async function fetchB2B(params: FilterParams) {
  return fetchJSON(`${API_BASE}/b2b-analytics?${buildQueryString(params)}`)
}

export async function fetchStaffRevenue(params: FilterParams) {
  return fetchJSON(`${API_BASE}/staff-revenue?${buildQueryString(params)}`)
}

export async function fetchOrderList(params: FilterParams) {
  return fetchJSON(`${API_BASE}/order-list?${buildQueryString(params)}`)
}

export async function fetchInventoryByCategory(params: FilterParams) {
  return fetchJSON(`${API_BASE}/inventory-by-category?${buildQueryString(params)}`)
}

export async function fetchDrillDown(params: FilterParams, req: DrillDownRequest) {
  const qs = buildQueryString(params)
  const extra = new URLSearchParams()
  if (req.clickedValue) extra.set('clicked_value', req.clickedValue)
  const extraStr = extra.toString()
  return fetchJSON(`${API_BASE}/drill-down/${req.metricKey}?${qs}${extraStr ? '&' + extraStr : ''}`)
}

export async function sendChatMessage(message: string, history: { role: string; content: string }[]) {
  const token = localStorage.getItem('edp_token')
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': token ? `Bearer ${token}` : '',
    },
    body: JSON.stringify({ message, history }),
  })
  if (res.status === 401) {
    logout()
    throw new Error('Unauthorized')
  }
  if (!res.ok) throw new Error(`API error: ${res.status}`)
  return res.json() as Promise<{ ok: boolean; response?: string; error?: string }>
}

export async function fetchChatConfig() {
  return fetchJSON<{ ok: boolean; provider: string; model: string }>(`${API_BASE}/chat/config`)
}

