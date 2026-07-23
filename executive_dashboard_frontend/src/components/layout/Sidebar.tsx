import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Star,
  Trophy,
  SmilePlus,
  Users,
  Building2,
  MessageSquare,
  ClipboardList,
  Menu,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { PageType } from '@/types'

interface SidebarProps {
  currentPage: PageType
  onNavigate: (page: PageType) => void
  onLogout?: () => void
  user?: { username: string; role: string } | null
}

const navItems: { id: PageType; label: string; icon: typeof LayoutDashboard }[] = [
  { id: 'executive', label: 'Tổng quan', icon: LayoutDashboard },
  { id: 'sales', label: 'Bán hàng & Marketing', icon: ShoppingCart },
  { id: 'order-list', label: 'Đơn hàng', icon: ClipboardList },
  { id: 'inventory', label: 'Tồn kho', icon: Package },
  { id: 'quality', label: 'Chất lượng & CLV', icon: Star },
  { id: 'leaderboard', label: 'Xếp hạng CH', icon: Trophy },
  { id: 'csat', label: 'CSAT theo CH', icon: SmilePlus },
  { id: 'revenue-staff', label: 'DT / Nhân viên', icon: Users },
  { id: 'b2b', label: 'B2B Analytics', icon: Building2 },
  { id: 'conversation', label: 'Chat Analytics', icon: MessageSquare },
]

export function Sidebar({ currentPage, onNavigate, onLogout, user }: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <>
      {/* Mobile hamburger */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed top-4 left-4 z-50 md:hidden p-2 bg-slate-900 text-white rounded-lg"
        aria-label="Open menu"
      >
        <Menu size={20} />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 left-0 h-full w-64 bg-slate-900 text-white z-50 flex flex-col transition-transform duration-300',
          'md:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        )}
      >
        {/* Logo / brand */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">
              R
            </div>
            <span className="text-lg font-bold">Rocky Lens</span>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            className="md:hidden p-1 hover:bg-slate-700 rounded"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => {
                onNavigate(id)
                setMobileOpen(false)
              }}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                currentPage === id
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              )}
            >
              <Icon size={18} />
              {label}
            </button>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-4 border-t border-slate-700">
          {user && (
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-slate-300 truncate">{user.username} ({user.role})</span>
              {onLogout && (
                <button
                  onClick={onLogout}
                  className="text-xs text-slate-400 hover:text-white transition-colors"
                >
                  Logout
                </button>
              )}
            </div>
          )}
          <p className="text-xs text-slate-400">HMK Rocky v1.0</p>
        </div>
      </aside>
    </>
  )
}
