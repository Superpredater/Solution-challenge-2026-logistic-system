import apiClient from './client'
import type { User } from '../types'

export interface LoginRequest {
  email: string
  password: string
  totp_code?: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
  mfa_required?: boolean
}

export interface RegisterRequest {
  name: string
  email: string
  password: string
  company: string
  role?: string
}

export interface RegisterResponse {
  access_token: string
  token_type: string
  user: User
}

export const login = async (data: LoginRequest): Promise<LoginResponse> => {
  const res = await apiClient.post<LoginResponse>('/api/v1/auth/login', data)
  return res.data
}

export const register = async (data: RegisterRequest): Promise<RegisterResponse> => {
  const res = await apiClient.post<RegisterResponse>('/api/v1/auth/register', data)
  return res.data
}

export const logout = async (): Promise<void> => {
  try {
    await apiClient.post('/api/v1/auth/logout')
  } catch {
    // ignore errors on logout
  }
}

export const getMe = async (): Promise<User> => {
  const res = await apiClient.get<User>('/api/v1/auth/me')
  return res.data
}

// ─── Demo Accounts ────────────────────────────────────────────────────────────

export interface DemoAccount {
  id: string
  name: string
  email: string
  password: string
  role: string
  description: string
  color: string
}

export const DEMO_ACCOUNTS: DemoAccount[] = [
  {
    id: 'demo-admin-0001',
    name: 'Alex Admin',
    email: 'admin@demo.com',
    password: 'demo1234',
    role: 'Admin',
    description: 'Full access — configure tenant, manage users, API keys',
    color: '#ef4444',
  },
  {
    id: 'demo-manager-0002',
    name: 'Morgan Manager',
    email: 'manager@demo.com',
    password: 'demo1234',
    role: 'Manager',
    description: 'Approve reroutes, override decisions, view audit trail',
    color: '#f59e0b',
  },
  {
    id: 'demo-analyst-0003',
    name: 'Sam Analyst',
    email: 'analyst@demo.com',
    password: 'demo1234',
    role: 'Analyst',
    description: 'Generate reports, query AI assistant, view all data',
    color: '#3b82f6',
  },
  {
    id: 'demo-viewer-0004',
    name: 'Jordan Viewer',
    email: 'viewer@demo.com',
    password: 'demo1234',
    role: 'Viewer',
    description: 'Read-only access to dashboard, shipments, and alerts',
    color: '#22c55e',
  },
]
