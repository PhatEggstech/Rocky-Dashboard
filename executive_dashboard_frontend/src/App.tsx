import { useState, useCallback } from 'react'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { DrillDownPanel } from '@/components/ui/DrillDownPanel'
import type { DrillDownData } from '@/components/ui/DrillDownPanel'
import { ExecutiveSummary } from '@/pages/ExecutiveSummary'
import { SalesMarketing } from '@/pages/SalesMarketing'
import { InventorySupplyChain } from '@/pages/InventorySupplyChain'
import { QualityCLV } from '@/pages/QualityCLV'
import { StoreLeaderboard } from '@/pages/StoreLeaderboard'
import { CsatByStore } from '@/pages/CsatByStore'
import { RevenuePerStaff } from '@/pages/RevenuePerStaff'
import { OrderList } from '@/pages/OrderList'
import { B2BAnalytics } from '@/pages/B2BAnalytics'
import { ConversationAnalytics } from '@/pages/ConversationAnalytics'
import { LoginPage } from '@/pages/LoginPage'
import { fetchDrillDown, logout } from '@/lib/api'
import type { PageType, FilterParams, DrillDownRequest } from '@/types'

function getDefaultFilters(): FilterParams {
  const today = new Date()
  const start = new Date(today.getFullYear(), today.getMonth(), 1)
  return {
    start: start.toISOString().slice(0, 10),
    end: today.toISOString().slice(0, 10),
    period: 'day',
  }
}

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('edp_token'))
  const [user, setUser] = useState<{ username: string; role: string } | null>(null)
  const [currentPage, setCurrentPage] = useState<PageType>('executive')
  const [filters, setFilters] = useState<FilterParams>(getDefaultFilters)
  const [drillDownData, setDrillDownData] = useState<DrillDownData | null>(null)
  const [drillDownLoading, setDrillDownLoading] = useState(false)

  const handleLogin = useCallback((_token: string, userData: { username: string; role: string }) => {
    setIsAuthenticated(true)
    setUser(userData)
  }, [])

  const handleLogout = useCallback(() => {
    logout()
  }, [])

  const handleDrillDown = useCallback(
    (req: DrillDownRequest) => {
      setDrillDownLoading(true)
      setDrillDownData(null)
      fetchDrillDown(filters, req)
        .then((d) => setDrillDownData(d as DrillDownData))
        .catch(console.error)
        .finally(() => setDrillDownLoading(false))
    },
    [filters]
  )

  const closeDrillDown = useCallback(() => {
    setDrillDownData(null)
    setDrillDownLoading(false)
  }, [])

  if (!isAuthenticated) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Sidebar currentPage={currentPage} onNavigate={setCurrentPage} onLogout={handleLogout} user={user} />

      {/* Main content area: offset by sidebar width on desktop */}
      <div className="md:ml-64">
        <Header filters={filters} onFiltersChange={setFilters} />

        <main className="p-6">
          {currentPage === 'executive' && <ExecutiveSummary filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'sales' && <SalesMarketing filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'inventory' && <InventorySupplyChain filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'quality' && <QualityCLV filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'leaderboard' && <StoreLeaderboard filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'csat' && <CsatByStore filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'revenue-staff' && <RevenuePerStaff filters={filters} onDrillDown={handleDrillDown} />}
          {currentPage === 'order-list' && <OrderList filters={filters} />}
          {currentPage === 'b2b' && <B2BAnalytics onDrillDown={handleDrillDown} />}
          {currentPage === 'conversation' && <ConversationAnalytics />}
        </main>
      </div>

      {/* Drill-down slide-over panel */}
      <DrillDownPanel
        data={drillDownData}
        loading={drillDownLoading}
        onClose={closeDrillDown}
      />
    </div>
  )
}
