import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Role, User } from '../types'

interface AuthState {
  token: string | null
  user: User | null
  role: Role | null
  tenantId: string | null
  isAuthenticated: boolean
  setAuth: (token: string, user: User) => void
  updateUser: (updates: Partial<User>) => void
  clearAuth: () => void
  hasRole: (minRole: Role) => boolean
}

const ROLE_HIERARCHY: Record<Role, number> = {
  Viewer: 0,
  Analyst: 1,
  Manager: 2,
  Admin: 3,
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      user: null,
      role: null,
      tenantId: null,
      isAuthenticated: false,

      setAuth: (token, user) =>
        set({
          token,
          user,
          role: user.role,
          tenantId: user.tenant_id,
          isAuthenticated: true,
        }),

      updateUser: (updates) =>
        set((state) => ({
          user: state.user ? { ...state.user, ...updates } : state.user,
        })),

      clearAuth: () =>
        set({
          token: null,
          user: null,
          role: null,
          tenantId: null,
          isAuthenticated: false,
        }),

      hasRole: (minRole) => {
        const { role } = get()
        if (!role) return false
        return ROLE_HIERARCHY[role] >= ROLE_HIERARCHY[minRole]
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
        role: state.role,
        tenantId: state.tenantId,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)
