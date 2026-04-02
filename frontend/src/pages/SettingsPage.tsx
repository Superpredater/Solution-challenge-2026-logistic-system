import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Settings, Save, Plus, Trash2, Key, Shield, Leaf, Cpu } from 'lucide-react'
import apiClient from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useUIStore } from '../store/uiStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

interface TenantSettings {
  tenant_id: string
  name: string
  mfa_enabled: boolean
  eco_routing_enabled: boolean
  autonomous_decision_enabled: boolean
  risk_score_weights: {
    w_weather: number
    w_operational: number
    w_war: number
    w_geopolitical: number
  }
  quiet_period_start?: string
  quiet_period_end?: string
  custom_risk_thresholds: { name: string; threshold: number; severity: string }[]
}

interface ApiKey {
  key_id: string
  name: string
  key_prefix: string
  created_at: string
  last_used_at?: string
  rate_limit_per_minute: number
}

async function getTenantSettings(): Promise<TenantSettings> {
  const res = await apiClient.get('/api/v1/settings/tenant')
  return res.data
}

async function updateTenantSettings(data: Partial<TenantSettings>): Promise<TenantSettings> {
  const res = await apiClient.patch('/api/v1/settings/tenant', data)
  return res.data
}

async function getApiKeys(): Promise<ApiKey[]> {
  const res = await apiClient.get('/api/v1/settings/api-keys')
  return res.data
}

async function createApiKey(name: string): Promise<{ key: string; key_id: string }> {
  const res = await apiClient.post('/api/v1/settings/api-keys', { name })
  return res.data
}

async function deleteApiKey(id: string): Promise<void> {
  await apiClient.delete(`/api/v1/settings/api-keys/${id}`)
}

type SettingsTab = 'general' | 'risk' | 'api-keys'

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const addToast = useUIStore((s) => s.addToast)
  const tenantId = useAuthStore((s) => s.tenantId)
  const [activeTab, setActiveTab] = useState<SettingsTab>('general')
  const [newKeyName, setNewKeyName] = useState('')
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)
  const [newThresholdName, setNewThresholdName] = useState('')
  const [newThresholdValue, setNewThresholdValue] = useState(70)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['tenant-settings'],
    queryFn: getTenantSettings,
  })

  const { data: apiKeys, isLoading: keysLoading } = useQuery({
    queryKey: ['api-keys'],
    queryFn: getApiKeys,
    enabled: activeTab === 'api-keys',
  })

  const [localSettings, setLocalSettings] = useState<Partial<TenantSettings>>({})

  const effectiveSettings = { ...settings, ...localSettings } as TenantSettings

  const updateMutation = useMutation({
    mutationFn: updateTenantSettings,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant-settings'] })
      setLocalSettings({})
      addToast({ type: 'success', title: 'Settings saved' })
    },
    onError: () => {
      addToast({ type: 'error', title: 'Failed to save settings' })
    },
  })

  const createKeyMutation = useMutation({
    mutationFn: createApiKey,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setNewKeyValue(data.key)
      setNewKeyName('')
      addToast({ type: 'success', title: 'API key created', message: 'Copy it now — it won\'t be shown again' })
    },
    onError: () => {
      addToast({ type: 'error', title: 'Failed to create API key' })
    },
  })

  const deleteKeyMutation = useMutation({
    mutationFn: deleteApiKey,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      addToast({ type: 'info', title: 'API key deleted' })
    },
  })

  const handleSave = () => {
    if (Object.keys(localSettings).length === 0) return
    updateMutation.mutate(localSettings)
  }

  const patch = (updates: Partial<TenantSettings>) => {
    setLocalSettings((prev) => ({ ...prev, ...updates }))
  }

  const weightsSum = effectiveSettings?.risk_score_weights
    ? Object.values(effectiveSettings.risk_score_weights).reduce((a, b) => a + b, 0)
    : 1

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Settings size={24} className="text-accent-blue" />
          <div>
            <h1 className="text-text-primary text-2xl font-bold">Settings</h1>
            <p className="text-text-secondary text-sm mt-0.5">Tenant configuration</p>
          </div>
        </div>
        {Object.keys(localSettings).length > 0 && (
          <button
            onClick={handleSave}
            disabled={updateMutation.isPending}
            className="btn-primary flex items-center gap-2"
          >
            {updateMutation.isPending ? <LoadingSpinner size="sm" /> : <Save size={16} />}
            Save Changes
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface rounded-xl p-1 w-fit">
        {[
          { id: 'general' as SettingsTab, label: 'General', icon: Shield },
          { id: 'risk' as SettingsTab, label: 'Risk Weights', icon: Cpu },
          { id: 'api-keys' as SettingsTab, label: 'API Keys', icon: Key },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              activeTab === id
                ? 'bg-card text-text-primary shadow-sm'
                : 'text-text-secondary hover:text-text-primary'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* General Settings */}
      {activeTab === 'general' && effectiveSettings && (
        <div className="space-y-4">
          <div className="card space-y-5">
            <h2 className="text-text-primary font-semibold">Platform Features</h2>

            {[
              {
                key: 'mfa_enabled' as const,
                label: 'Multi-Factor Authentication',
                description: 'Require TOTP for all users in this tenant',
                icon: Shield,
              },
              {
                key: 'eco_routing_enabled' as const,
                label: 'Eco-Friendly Routing',
                description: 'Prioritize routes with lower CO₂ emissions',
                icon: Leaf,
              },
              {
                key: 'autonomous_decision_enabled' as const,
                label: 'Autonomous Decision Engine',
                description: 'Allow system to auto-apply reroute recommendations',
                icon: Cpu,
              },
            ].map(({ key, label, description, icon: Icon }) => (
              <div key={key} className="flex items-center justify-between">
                <div className="flex items-start gap-3">
                  <Icon size={18} className="text-text-muted mt-0.5" />
                  <div>
                    <p className="text-text-primary text-sm font-medium">{label}</p>
                    <p className="text-text-muted text-xs">{description}</p>
                  </div>
                </div>
                <button
                  onClick={() => patch({ [key]: !effectiveSettings[key] })}
                  className={`relative w-11 h-6 rounded-full transition-colors ${
                    effectiveSettings[key] ? 'bg-accent-blue' : 'bg-border'
                  }`}
                >
                  <span
                    className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                      effectiveSettings[key] ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
              </div>
            ))}
          </div>

          {/* Quiet Period */}
          <div className="card space-y-4">
            <h2 className="text-text-primary font-semibold">Quiet Period</h2>
            <p className="text-text-secondary text-sm">
              Suppress non-critical alerts during this time window (UTC)
            </p>
            <div className="flex items-center gap-4">
              <div>
                <label className="block text-text-secondary text-xs mb-1">Start Time</label>
                <input
                  type="time"
                  value={effectiveSettings.quiet_period_start || ''}
                  onChange={(e) => patch({ quiet_period_start: e.target.value })}
                  className="input w-36"
                />
              </div>
              <span className="text-text-muted mt-5">to</span>
              <div>
                <label className="block text-text-secondary text-xs mb-1">End Time</label>
                <input
                  type="time"
                  value={effectiveSettings.quiet_period_end || ''}
                  onChange={(e) => patch({ quiet_period_end: e.target.value })}
                  className="input w-36"
                />
              </div>
            </div>
          </div>

          {/* Custom Risk Thresholds */}
          <div className="card space-y-4">
            <h2 className="text-text-primary font-semibold">Custom Risk Thresholds</h2>
            <div className="space-y-2">
              {(effectiveSettings.custom_risk_thresholds || []).map((t, i) => (
                <div key={i} className="flex items-center gap-3 bg-surface rounded-lg px-3 py-2">
                  <span className="text-text-primary text-sm flex-1">{t.name}</span>
                  <span className="text-text-secondary text-sm">≥ {t.threshold}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-accent-amber/20 text-accent-amber">
                    {t.severity}
                  </span>
                  <button
                    onClick={() => {
                      const updated = (effectiveSettings.custom_risk_thresholds || []).filter((_, j) => j !== i)
                      patch({ custom_risk_thresholds: updated })
                    }}
                    className="text-text-muted hover:text-accent-red transition-colors"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))}
              <div className="flex gap-2">
                <input
                  type="text"
                  value={newThresholdName}
                  onChange={(e) => setNewThresholdName(e.target.value)}
                  placeholder="Threshold name"
                  className="input flex-1 text-sm"
                />
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={newThresholdValue}
                  onChange={(e) => setNewThresholdValue(Number(e.target.value))}
                  className="input w-20 text-sm"
                />
                <button
                  onClick={() => {
                    if (newThresholdName.trim()) {
                      const updated = [
                        ...(effectiveSettings.custom_risk_thresholds || []),
                        { name: newThresholdName, threshold: newThresholdValue, severity: 'Warning' },
                      ]
                      patch({ custom_risk_thresholds: updated })
                      setNewThresholdName('')
                      setNewThresholdValue(70)
                    }
                  }}
                  className="btn-secondary px-3"
                >
                  <Plus size={14} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Weights */}
      {activeTab === 'risk' && effectiveSettings?.risk_score_weights && (
        <div className="card space-y-5">
          <div className="flex items-center justify-between">
            <h2 className="text-text-primary font-semibold">Risk Score Weights</h2>
            <span
              className={`text-sm font-medium ${
                Math.abs(weightsSum - 1) < 0.01 ? 'text-accent-green' : 'text-accent-red'
              }`}
            >
              Sum: {weightsSum.toFixed(2)} {Math.abs(weightsSum - 1) < 0.01 ? '✓' : '(must equal 1.0)'}
            </span>
          </div>
          <p className="text-text-secondary text-sm">
            Adjust how each dimension contributes to the unified risk score.
          </p>
          {[
            { key: 'w_weather' as const, label: 'Weather Risk', color: '#3b82f6' },
            { key: 'w_operational' as const, label: 'Operational Risk', color: '#f59e0b' },
            { key: 'w_war' as const, label: 'War State Risk', color: '#ef4444' },
            { key: 'w_geopolitical' as const, label: 'Geopolitical Risk', color: '#f97316' },
          ].map(({ key, label, color }) => {
            const value = effectiveSettings.risk_score_weights[key]
            return (
              <div key={key}>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-text-secondary">{label}</span>
                  <span className="text-text-primary font-medium">{(value * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={value}
                  onChange={(e) => {
                    const newWeights = {
                      ...effectiveSettings.risk_score_weights,
                      [key]: Number(e.target.value),
                    }
                    patch({ risk_score_weights: newWeights })
                  }}
                  className="w-full"
                  style={{ accentColor: color }}
                />
              </div>
            )
          })}
        </div>
      )}

      {/* API Keys */}
      {activeTab === 'api-keys' && (
        <div className="space-y-4">
          {newKeyValue && (
            <div className="card border-accent-green/30 bg-accent-green/5">
              <p className="text-accent-green font-semibold text-sm mb-2">New API Key Created</p>
              <p className="text-text-secondary text-xs mb-3">
                Copy this key now. It will not be shown again.
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 bg-surface rounded-lg px-3 py-2 text-text-primary text-xs font-mono break-all">
                  {newKeyValue}
                </code>
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(newKeyValue)
                    addToast({ type: 'success', title: 'Copied to clipboard' })
                  }}
                  className="btn-secondary text-xs py-2"
                >
                  Copy
                </button>
              </div>
              <button
                onClick={() => setNewKeyValue(null)}
                className="text-text-muted text-xs mt-2 hover:text-text-primary"
              >
                Dismiss
              </button>
            </div>
          )}

          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-text-primary font-semibold">API Keys</h2>
            </div>

            {/* Create new key */}
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="Key name (e.g. Production Integration)"
                className="input flex-1"
                onKeyDown={(e) => e.key === 'Enter' && newKeyName.trim() && createKeyMutation.mutate(newKeyName)}
              />
              <button
                onClick={() => newKeyName.trim() && createKeyMutation.mutate(newKeyName)}
                disabled={!newKeyName.trim() || createKeyMutation.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {createKeyMutation.isPending ? <LoadingSpinner size="sm" /> : <Plus size={16} />}
                Create
              </button>
            </div>

            {/* Keys list */}
            {keysLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : (apiKeys || []).length === 0 ? (
              <p className="text-text-muted text-sm text-center py-8">No API keys created yet</p>
            ) : (
              <div className="space-y-2">
                {(apiKeys || []).map((key) => (
                  <div key={key.key_id} className="flex items-center justify-between bg-surface rounded-lg px-4 py-3">
                    <div>
                      <p className="text-text-primary text-sm font-medium">{key.name}</p>
                      <div className="flex items-center gap-3 mt-0.5">
                        <code className="text-text-muted text-xs font-mono">{key.key_prefix}...</code>
                        <span className="text-text-muted text-xs">
                          {key.rate_limit_per_minute} req/min
                        </span>
                        {key.last_used_at && (
                          <span className="text-text-muted text-xs">
                            Last used: {new Date(key.last_used_at).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    </div>
                    <button
                      onClick={() => deleteKeyMutation.mutate(key.key_id)}
                      className="text-text-muted hover:text-accent-red transition-colors p-1.5"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
