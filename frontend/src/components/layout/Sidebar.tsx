import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Map,
  Package,
  Bell,
  AlertTriangle,
  Truck,
  Globe,
  Cpu,
  BarChart2,
  Bot,
  ClipboardList,
  Leaf,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'
import { useUIStore } from '../../store/uiStore'
import { useAuthStore } from '../../store/authStore'

const NAV_ITEMS = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard', exact: true },
  { to: '/map', icon: Map, label: 'Live Map' },
  { to: '/shipments', icon: Package, label: 'Shipments' },
  { to: '/alerts', icon: Bell, label: 'Alerts', badge: true },
  { to: '/disruptions', icon: AlertTriangle, label: 'Disruptions' },
  { to: '/carriers', icon: Truck, label: 'Carriers' },
  { to: '/regions', icon: Globe, label: 'Regions' },
  { to: '/digital-twin', icon: Cpu, label: 'Digital Twin' },
  { to: '/reports', icon: BarChart2, label: 'Reports' },
  { to: '/ai-chat', icon: Bot, label: 'AI Assistant' },
  { to: '/carbon', icon: Leaf, label: 'Carbon' },
]

const MANAGER_ITEMS = [
  { to: '/decision-audit', icon: ClipboardList, label: 'Decision Audit' },
]

const BOTTOM_ITEMS = [
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, unreadAlertCount } = useUIStore()
  const { hasRole } = useAuthStore()

  return (
    <aside
      className={clsx(
        'flex flex-col bg-surface border-r border-border transition-all duration-300 shrink-0',
        sidebarCollapsed ? 'w-16' : 'w-60'
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-4 border-b border-border">
        <div className="w-8 h-8 rounded-lg bg-accent-blue flex items-center justify-center shrink-0">
          <Zap size={16} className="text-white" />
        </div>
        {!sidebarCollapsed && (
          <span className="font-bold text-text-primary text-sm leading-tight">
            Supply Chain<br />
            <span className="text-accent-blue">Intelligence</span>
          </span>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV_ITEMS.map(({ to, icon: Icon, label, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group relative',
                isActive
                  ? 'bg-accent-blue/15 text-accent-blue'
                  : 'text-text-secondary hover:bg-card hover:text-text-primary'
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            {!sidebarCollapsed && <span className="truncate">{label}</span>}
            {badge && unreadAlertCount > 0 && (
              <span
                className={clsx(
                  'bg-accent-red text-white text-xs font-bold rounded-full flex items-center justify-center',
                  sidebarCollapsed
                    ? 'absolute top-1 right-1 w-4 h-4 text-[10px]'
                    : 'ml-auto w-5 h-5'
                )}
              >
                {unreadAlertCount > 99 ? '99+' : unreadAlertCount}
              </span>
            )}
            {sidebarCollapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-card border border-border rounded-lg text-xs text-text-primary whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                {label}
              </div>
            )}
          </NavLink>
        ))}

        {hasRole('Manager') && (
          <>
            <div className="my-2 border-t border-border" />
            {MANAGER_ITEMS.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group relative',
                    isActive
                      ? 'bg-accent-blue/15 text-accent-blue'
                      : 'text-text-secondary hover:bg-card hover:text-text-primary'
                  )
                }
              >
                <Icon size={18} className="shrink-0" />
                {!sidebarCollapsed && <span className="truncate">{label}</span>}
                {sidebarCollapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-card border border-border rounded-lg text-xs text-text-primary whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50">
                    {label}
                  </div>
                )}
              </NavLink>
            ))}
          </>
        )}
      </nav>

      {/* Bottom */}
      <div className="border-t border-border py-3 px-2 space-y-0.5">
        {BOTTOM_ITEMS.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors group relative',
                isActive
                  ? 'bg-accent-blue/15 text-accent-blue'
                  : 'text-text-secondary hover:bg-card hover:text-text-primary'
              )
            }
          >
            <Icon size={18} className="shrink-0" />
            {!sidebarCollapsed && <span className="truncate">{label}</span>}
          </NavLink>
        ))}

        <button
          onClick={toggleSidebar}
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-text-muted hover:text-text-primary hover:bg-card transition-colors w-full"
        >
          {sidebarCollapsed ? <ChevronRight size={18} /> : <ChevronLeft size={18} />}
          {!sidebarCollapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  )
}
