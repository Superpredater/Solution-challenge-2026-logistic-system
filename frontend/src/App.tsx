import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { Layout } from './components/layout/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Shipments from './pages/Shipments'
import ShipmentDetail from './pages/ShipmentDetail'
import AlertsPage from './pages/AlertsPage'
import MapPage from './pages/MapPage'
import CarriersPage from './pages/CarriersPage'
import ReportsPage from './pages/ReportsPage'
import DigitalTwinPage from './pages/DigitalTwinPage'
import DecisionAuditPage from './pages/DecisionAuditPage'
import AIAssistantPage from './pages/AIAssistantPage'
import SettingsPage from './pages/SettingsPage'
import CarbonPage from './pages/CarbonPage'
import DisruptionsPage from './pages/DisruptionsPage'
import RegionsPage from './pages/RegionsPage'
import ProfilePage from './pages/ProfilePage'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireRole({
  children,
  minRole,
}: {
  children: React.ReactNode
  minRole: 'Manager' | 'Admin'
}) {
  const hasRole = useAuthStore((s) => s.hasRole)
  const role = useAuthStore((s) => s.role)
  if (!hasRole(minRole)) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <div className="w-14 h-14 rounded-full bg-accent-amber/20 flex items-center justify-center">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" strokeWidth="2">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
          </svg>
        </div>
        <div className="text-center">
          <p className="text-text-primary font-semibold text-lg">Access Restricted</p>
          <p className="text-text-secondary text-sm mt-1">
            This page requires <span className="text-accent-amber font-medium">{minRole}</span> or higher.
          </p>
          <p className="text-text-muted text-xs mt-1">
            Your current role: <span className="font-medium text-text-secondary">{role}</span>
          </p>
        </div>
        <a href="/" className="text-accent-blue text-sm hover:underline">← Back to Dashboard</a>
      </div>
    )
  }
  return <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Dashboard />} />
          <Route path="shipments" element={<Shipments />} />
          <Route path="shipments/:id" element={<ShipmentDetail />} />
          <Route path="alerts" element={<AlertsPage />} />
          <Route path="map" element={<MapPage />} />
          <Route path="carriers" element={<CarriersPage />} />
          <Route path="reports" element={<ReportsPage />} />
          <Route path="ai-chat" element={<AIAssistantPage />} />
          <Route path="carbon" element={<CarbonPage />} />
          <Route path="disruptions" element={<DisruptionsPage />} />
          <Route path="regions" element={<RegionsPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="digital-twin" element={<DigitalTwinPage />} />
          <Route
            path="decision-audit"
            element={
              <RequireRole minRole="Manager">
                <DecisionAuditPage />
              </RequireRole>
            }
          />
          <Route
            path="settings"
            element={
              <RequireRole minRole="Admin">
                <SettingsPage />
              </RequireRole>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
