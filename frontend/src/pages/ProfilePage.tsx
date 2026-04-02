import { useState, useRef } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  User, Mail, Phone, Building2, Briefcase, MapPin, FileText,
  Camera, Save, Lock, Bell, Shield, CheckCircle, Eye, EyeOff,
} from 'lucide-react'
import apiClient from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useUIStore } from '../store/uiStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'
import type { Role } from '../types'

const ROLE_COLORS: Record<Role, { bg: string; text: string; border: string }> = {
  Admin:   { bg: 'bg-accent-red/20',   text: 'text-accent-red',   border: 'border-accent-red/30' },
  Manager: { bg: 'bg-accent-amber/20', text: 'text-accent-amber', border: 'border-accent-amber/30' },
  Analyst: { bg: 'bg-accent-blue/20',  text: 'text-accent-blue',  border: 'border-accent-blue/30' },
  Viewer:  { bg: 'bg-surface',         text: 'text-text-secondary', border: 'border-border' },
}

const ROLE_PERMISSIONS: Record<Role, string[]> = {
  Admin:   ['Full platform access', 'User management', 'Tenant configuration', 'API key management', 'Autonomous mode control'],
  Manager: ['Approve/reject reroutes', 'Manual override decisions', 'View decision audit trail', 'Run simulations', 'Generate reports'],
  Analyst: ['Generate reports', 'Query AI assistant', 'View all shipments & alerts', 'Run digital twin scenarios'],
  Viewer:  ['Read-only dashboard access', 'View shipments & alerts', 'View map & carriers'],
}

async function fetchProfile() {
  const res = await apiClient.get('/api/v1/profile')
  return res.data
}

async function saveProfile(data: Record<string, string>) {
  const res = await apiClient.patch('/api/v1/profile', data)
  return res.data
}

async function changePassword(data: { current_password: string; new_password: string }) {
  const res = await apiClient.post('/api/v1/profile/change-password', data)
  return res.data
}

function AvatarUpload({ avatar, name, onUpload }: {
  avatar?: string; name?: string; onUpload: (b64: string) => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const initials = (name || 'U').split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.size > 2 * 1024 * 1024) { alert('Image must be under 2MB'); return }
    const reader = new FileReader()
    reader.onload = () => onUpload(reader.result as string)
    reader.readAsDataURL(file)
  }

  return (
    <div className="relative group w-fit">
      <div className="w-24 h-24 rounded-full overflow-hidden border-4 border-border bg-surface flex items-center justify-center">
        {avatar ? (
          <img src={avatar} alt="Avatar" className="w-full h-full object-cover" />
        ) : (
          <span className="text-2xl font-bold text-accent-blue">{initials}</span>
        )}
      </div>
      <button
        onClick={() => fileRef.current?.click()}
        className="absolute inset-0 rounded-full bg-black/50 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
      >
        <Camera size={20} className="text-white" />
      </button>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
      <button
        onClick={() => fileRef.current?.click()}
        className="absolute -bottom-1 -right-1 w-7 h-7 bg-accent-blue rounded-full flex items-center justify-center border-2 border-bg shadow-lg"
      >
        <Camera size={12} className="text-white" />
      </button>
    </div>
  )
}

export default function ProfilePage() {
  const queryClient = useQueryClient()
  const { user, role, updateUser } = useAuthStore()
  const addToast = useUIStore((s) => s.addToast)

  const [tab, setTab] = useState<'profile' | 'security' | 'notifications'>('profile')
  const [showCurrent, setShowCurrent] = useState(false)
  const [showNew, setShowNew] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  // Profile form
  const [form, setForm] = useState({
    name: user?.name || '',
    phone: user?.phone || '',
    company: user?.company || '',
    job_title: user?.job_title || '',
    bio: user?.bio || '',
    location: user?.location || '',
    avatar: user?.avatar || '',
  })

  // Password form
  const [pwForm, setPwForm] = useState({ current_password: '', new_password: '', confirm_password: '' })

  // Notification prefs (local only)
  const [notifPrefs, setNotifPrefs] = useState({
    email: true, sms: false, webhook: false,
    critical_only: false, quiet_start: '22:00', quiet_end: '07:00',
  })

  const { data: profileData, isLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: fetchProfile,
    onSuccess: (data) => {
      setForm({
        name: data.name || '',
        phone: data.phone || '',
        company: data.company || '',
        job_title: data.job_title || '',
        bio: data.bio || '',
        location: data.location || '',
        avatar: data.avatar || '',
      })
    },
  })

  const saveMutation = useMutation({
    mutationFn: saveProfile,
    onSuccess: (data) => {
      updateUser(data)
      queryClient.invalidateQueries({ queryKey: ['profile'] })
      addToast({ type: 'success', title: 'Profile updated', message: 'Your changes have been saved' })
    },
    onError: () => addToast({ type: 'error', title: 'Failed to save profile' }),
  })

  const pwMutation = useMutation({
    mutationFn: changePassword,
    onSuccess: () => {
      setPwForm({ current_password: '', new_password: '', confirm_password: '' })
      addToast({ type: 'success', title: 'Password changed', message: 'Your password has been updated' })
    },
    onError: (err: any) => addToast({ type: 'error', title: err?.response?.data?.detail || 'Failed to change password' }),
  })

  const handleSave = () => {
    const payload: Record<string, string> = {}
    Object.entries(form).forEach(([k, v]) => { if (v !== undefined) payload[k] = v })
    saveMutation.mutate(payload)
  }

  const handlePasswordChange = () => {
    if (pwForm.new_password !== pwForm.confirm_password) {
      addToast({ type: 'error', title: 'Passwords do not match' }); return
    }
    if (pwForm.new_password.length < 8) {
      addToast({ type: 'error', title: 'Password must be at least 8 characters' }); return
    }
    pwMutation.mutate({ current_password: pwForm.current_password, new_password: pwForm.new_password })
  }

  const roleStyle = ROLE_COLORS[role || 'Viewer']
  const displayName = form.name || user?.email?.split('@')[0] || 'User'

  if (isLoading) return <div className="flex justify-center py-20"><LoadingSpinner size="lg" /></div>

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header card */}
      <div className="card">
        <div className="flex items-start gap-6 flex-wrap">
          <AvatarUpload
            avatar={form.avatar}
            name={form.name}
            onUpload={(b64) => setForm(f => ({ ...f, avatar: b64 }))}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 flex-wrap mb-1">
              <h1 className="text-text-primary text-2xl font-bold">{displayName}</h1>
              <span className={`text-xs px-2.5 py-1 rounded-full font-semibold border ${roleStyle.bg} ${roleStyle.text} ${roleStyle.border}`}>
                {role}
              </span>
            </div>
            <p className="text-text-secondary text-sm">{user?.email}</p>
            {form.job_title && <p className="text-text-muted text-sm mt-0.5">{form.job_title}{form.company ? ` · ${form.company}` : ''}</p>}
            {form.location && <p className="text-text-muted text-xs mt-1 flex items-center gap-1"><MapPin size={11} />{form.location}</p>}
            {form.bio && <p className="text-text-secondary text-sm mt-2 max-w-lg">{form.bio}</p>}
          </div>
          {/* Role permissions */}
          <div className={`rounded-xl p-4 border ${roleStyle.border} ${roleStyle.bg} min-w-[200px]`}>
            <p className={`text-xs font-semibold mb-2 ${roleStyle.text}`}>Your Permissions</p>
            <ul className="space-y-1">
              {(ROLE_PERMISSIONS[role || 'Viewer'] || []).map(p => (
                <li key={p} className="flex items-center gap-1.5 text-xs text-text-secondary">
                  <CheckCircle size={11} className={roleStyle.text} />{p}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-surface rounded-xl p-1 w-fit">
        {[
          { id: 'profile' as const, label: 'Profile', icon: User },
          { id: 'security' as const, label: 'Security', icon: Lock },
          { id: 'notifications' as const, label: 'Notifications', icon: Bell },
        ].map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setTab(id)}
            className={`flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              tab === id ? 'bg-card text-text-primary shadow-sm' : 'text-text-secondary hover:text-text-primary'
            }`}>
            <Icon size={14} />{label}
          </button>
        ))}
      </div>

      {/* Profile tab */}
      {tab === 'profile' && (
        <div className="card space-y-5">
          <h2 className="text-text-primary font-semibold">Personal Information</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              { key: 'name', label: 'Full Name', icon: User, placeholder: 'Jane Smith' },
              { key: 'phone', label: 'Phone Number', icon: Phone, placeholder: '+1 (555) 000-0000' },
              { key: 'company', label: 'Company / Organization', icon: Building2, placeholder: 'Acme Logistics' },
              { key: 'job_title', label: 'Job Title', icon: Briefcase, placeholder: 'Logistics Manager' },
              { key: 'location', label: 'Location', icon: MapPin, placeholder: 'Dubai, UAE' },
            ].map(({ key, label, icon: Icon, placeholder }) => (
              <div key={key}>
                <label className="block text-text-secondary text-xs mb-1.5">{label}</label>
                <div className="relative">
                  <Icon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={(form as any)[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    placeholder={placeholder}
                    className="input pl-9"
                  />
                </div>
              </div>
            ))}
            <div>
              <label className="block text-text-secondary text-xs mb-1.5">Email Address</label>
              <div className="relative">
                <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input type="email" value={user?.email || ''} disabled className="input pl-9 opacity-60 cursor-not-allowed" />
              </div>
              <p className="text-text-muted text-xs mt-1">Email cannot be changed</p>
            </div>
          </div>

          <div>
            <label className="block text-text-secondary text-xs mb-1.5">Bio</label>
            <div className="relative">
              <FileText size={14} className="absolute left-3 top-3 text-text-muted" />
              <textarea
                value={form.bio}
                onChange={e => setForm(f => ({ ...f, bio: e.target.value }))}
                placeholder="Tell your team a bit about yourself..."
                rows={3}
                className="input pl-9 resize-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-between pt-2 border-t border-border">
            <p className="text-text-muted text-xs">
              Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-US', { month: 'long', year: 'numeric' }) : '—'}
            </p>
            <button onClick={handleSave} disabled={saveMutation.isPending}
              className="btn-primary flex items-center gap-2 disabled:opacity-50">
              {saveMutation.isPending ? <LoadingSpinner size="sm" /> : <Save size={15} />}
              Save Changes
            </button>
          </div>
        </div>
      )}

      {/* Security tab */}
      {tab === 'security' && (
        <div className="space-y-4">
          <div className="card space-y-4">
            <h2 className="text-text-primary font-semibold flex items-center gap-2">
              <Lock size={16} className="text-accent-blue" /> Change Password
            </h2>
            {[
              { key: 'current_password', label: 'Current Password', show: showCurrent, toggle: () => setShowCurrent(s => !s) },
              { key: 'new_password', label: 'New Password', show: showNew, toggle: () => setShowNew(s => !s) },
              { key: 'confirm_password', label: 'Confirm New Password', show: showConfirm, toggle: () => setShowConfirm(s => !s) },
            ].map(({ key, label, show, toggle }) => (
              <div key={key}>
                <label className="block text-text-secondary text-xs mb-1.5">{label}</label>
                <div className="relative">
                  <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type={show ? 'text' : 'password'}
                    value={(pwForm as any)[key]}
                    onChange={e => setPwForm(f => ({ ...f, [key]: e.target.value }))}
                    className="input pl-9 pr-10"
                    placeholder="••••••••"
                  />
                  <button type="button" onClick={toggle}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary">
                    {show ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
            ))}
            {pwForm.new_password && pwForm.confirm_password && pwForm.new_password !== pwForm.confirm_password && (
              <p className="text-accent-red text-xs">Passwords do not match</p>
            )}
            <button onClick={handlePasswordChange} disabled={pwMutation.isPending || !pwForm.current_password || !pwForm.new_password}
              className="btn-primary flex items-center gap-2 disabled:opacity-50">
              {pwMutation.isPending ? <LoadingSpinner size="sm" /> : <Lock size={15} />}
              Update Password
            </button>
          </div>

          <div className="card space-y-3">
            <h2 className="text-text-primary font-semibold flex items-center gap-2">
              <Shield size={16} className="text-accent-green" /> Account Security
            </h2>
            <div className="space-y-3">
              {[
                { label: 'Two-Factor Authentication', desc: 'Add an extra layer of security with TOTP', status: 'Not configured', statusColor: 'text-accent-amber' },
                { label: 'Active Sessions', desc: 'You are logged in on 1 device', status: 'View sessions', statusColor: 'text-accent-blue' },
                { label: 'Login History', desc: 'Last login: just now', status: 'View history', statusColor: 'text-accent-blue' },
              ].map(({ label, desc, status, statusColor }) => (
                <div key={label} className="flex items-center justify-between p-3 bg-surface rounded-lg">
                  <div>
                    <p className="text-text-primary text-sm font-medium">{label}</p>
                    <p className="text-text-muted text-xs">{desc}</p>
                  </div>
                  <span className={`text-xs font-medium ${statusColor}`}>{status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Notifications tab */}
      {tab === 'notifications' && (
        <div className="card space-y-5">
          <h2 className="text-text-primary font-semibold flex items-center gap-2">
            <Bell size={16} className="text-accent-blue" /> Notification Preferences
          </h2>

          <div>
            <p className="text-text-secondary text-xs font-semibold mb-3 uppercase tracking-wide">Delivery Channels</p>
            <div className="space-y-3">
              {[
                { key: 'email', label: 'Email Notifications', desc: `Alerts sent to ${user?.email}` },
                { key: 'sms', label: 'SMS Notifications', desc: form.phone ? `Alerts sent to ${form.phone}` : 'Add a phone number in Profile' },
                { key: 'webhook', label: 'Webhook Push', desc: 'POST alerts to your endpoint' },
              ].map(({ key, label, desc }) => (
                <div key={key} className="flex items-center justify-between p-3 bg-surface rounded-lg">
                  <div>
                    <p className="text-text-primary text-sm font-medium">{label}</p>
                    <p className="text-text-muted text-xs">{desc}</p>
                  </div>
                  <button onClick={() => setNotifPrefs(p => ({ ...p, [key]: !(p as any)[key] }))}
                    className={`relative w-10 h-5 rounded-full transition-colors ${(notifPrefs as any)[key] ? 'bg-accent-blue' : 'bg-border'}`}>
                    <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${(notifPrefs as any)[key] ? 'translate-x-5' : 'translate-x-0.5'}`} />
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className="border-t border-border pt-4">
            <p className="text-text-secondary text-xs font-semibold mb-3 uppercase tracking-wide">Alert Filtering</p>
            <div className="flex items-center justify-between p-3 bg-surface rounded-lg mb-3">
              <div>
                <p className="text-text-primary text-sm font-medium">Critical Alerts Only</p>
                <p className="text-text-muted text-xs">Suppress Informational and Warning alerts</p>
              </div>
              <button onClick={() => setNotifPrefs(p => ({ ...p, critical_only: !p.critical_only }))}
                className={`relative w-10 h-5 rounded-full transition-colors ${notifPrefs.critical_only ? 'bg-accent-blue' : 'bg-border'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform ${notifPrefs.critical_only ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-text-secondary text-xs mb-1.5">Quiet Period Start (UTC)</label>
                <input type="time" value={notifPrefs.quiet_start}
                  onChange={e => setNotifPrefs(p => ({ ...p, quiet_start: e.target.value }))}
                  className="input" />
              </div>
              <div>
                <label className="block text-text-secondary text-xs mb-1.5">Quiet Period End (UTC)</label>
                <input type="time" value={notifPrefs.quiet_end}
                  onChange={e => setNotifPrefs(p => ({ ...p, quiet_end: e.target.value }))}
                  className="input" />
              </div>
            </div>
          </div>

          <div className="flex justify-end pt-2 border-t border-border">
            <button onClick={() => addToast({ type: 'success', title: 'Notification preferences saved' })}
              className="btn-primary flex items-center gap-2">
              <Save size={15} /> Save Preferences
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
