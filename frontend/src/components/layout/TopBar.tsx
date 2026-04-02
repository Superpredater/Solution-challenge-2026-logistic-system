import { useState, useRef, useEffect } from 'react'
import { Bell, Search, LogOut, User, Settings, ChevronDown } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { useUIStore } from '../../store/uiStore'
import { logout } from '../../api/auth'
import clsx from 'clsx'

const ROLE_COLORS: Record<string, string> = {
  Admin:   'bg-accent-red/20 text-accent-red',
  Manager: 'bg-accent-amber/20 text-accent-amber',
  Analyst: 'bg-accent-blue/20 text-accent-blue',
  Viewer:  'bg-surface text-text-secondary',
}

export function TopBar() {
  const navigate = useNavigate()
  const { user, role, clearAuth } = useAuthStore()
  const { unreadAlertCount } = useUIStore()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close menu on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleLogout = async () => {
    try { await logout() } catch { /* ignore */ }
    clearAuth()
    navigate('/login')
  }

  const displayName = user?.name || user?.email?.split('@')[0] || 'User'
  const initials = displayName.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2)

  return (
    <header className="h-14 bg-surface border-b border-border flex items-center px-4 gap-4 shrink-0">
      {/* Search */}
      <div className="flex-1 max-w-md">
        <div className="relative">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
          <input type="text" placeholder="Search shipments, alerts..." className="input pl-9 h-8 text-xs" />
        </div>
      </div>

      <div className="flex items-center gap-3 ml-auto">
        {/* Notifications */}
        <button onClick={() => navigate('/alerts')}
          className="relative p-2 rounded-lg hover:bg-card transition-colors text-text-secondary hover:text-text-primary">
          <Bell size={18} />
          {unreadAlertCount > 0 && (
            <span className="absolute top-1 right-1 w-4 h-4 bg-accent-red text-white text-[10px] font-bold rounded-full flex items-center justify-center">
              {unreadAlertCount > 9 ? '9+' : unreadAlertCount}
            </span>
          )}
        </button>

        {/* User menu */}
        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setMenuOpen(o => !o)}
            className="flex items-center gap-2.5 p-1.5 rounded-xl hover:bg-card transition-colors"
          >
            {/* Avatar */}
            <div className="w-8 h-8 rounded-full overflow-hidden bg-accent-blue/20 flex items-center justify-center border border-border shrink-0">
              {user?.avatar ? (
                <img src={user.avatar} alt="avatar" className="w-full h-full object-cover" />
              ) : (
                <span className="text-xs font-bold text-accent-blue">{initials}</span>
              )}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-text-primary text-sm font-medium leading-none">{displayName}</p>
              {role && (
                <span className={clsx('text-xs px-1.5 py-0.5 rounded font-medium', ROLE_COLORS[role] || 'bg-surface text-text-secondary')}>
                  {role}
                </span>
              )}
            </div>
            <ChevronDown size={14} className={clsx('text-text-muted transition-transform hidden sm:block', menuOpen && 'rotate-180')} />
          </button>

          {/* Dropdown */}
          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 bg-card border border-border rounded-xl shadow-2xl z-50 overflow-hidden">
              {/* User info header */}
              <div className="px-4 py-3 border-b border-border">
                <p className="text-text-primary text-sm font-semibold">{displayName}</p>
                <p className="text-text-muted text-xs truncate">{user?.email}</p>
              </div>

              <div className="py-1">
                <button
                  onClick={() => { navigate('/profile'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
                >
                  <User size={15} /> View Profile
                </button>
                <button
                  onClick={() => { navigate('/settings'); setMenuOpen(false) }}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-text-secondary hover:bg-surface hover:text-text-primary transition-colors"
                >
                  <Settings size={15} /> Settings
                </button>
              </div>

              <div className="border-t border-border py-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-accent-red hover:bg-accent-red/10 transition-colors"
                >
                  <LogOut size={15} /> Sign Out
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
