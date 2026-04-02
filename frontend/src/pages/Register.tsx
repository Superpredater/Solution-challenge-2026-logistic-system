import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import {
  Zap,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
  User,
  Mail,
  Lock,
  Building2,
  ChevronRight,
} from 'lucide-react'
import { register } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

const ROLE_OPTIONS = [
  {
    value: 'Viewer',
    label: 'Viewer',
    description: 'Read-only access to dashboard and shipments',
    color: '#22c55e',
  },
  {
    value: 'Analyst',
    label: 'Analyst',
    description: 'Generate reports and query AI assistant',
    color: '#3b82f6',
  },
  {
    value: 'Manager',
    label: 'Manager',
    description: 'Approve reroutes and manage decisions',
    color: '#f59e0b',
  },
  {
    value: 'Admin',
    label: 'Admin',
    description: 'Full platform access and configuration',
    color: '#ef4444',
  },
]

function PasswordStrength({ password }: { password: string }) {
  const checks = [
    { label: 'At least 8 characters', ok: password.length >= 8 },
    { label: 'Contains uppercase', ok: /[A-Z]/.test(password) },
    { label: 'Contains number', ok: /\d/.test(password) },
    { label: 'Contains special character', ok: /[^A-Za-z0-9]/.test(password) },
  ]
  const score = checks.filter((c) => c.ok).length

  const barColor =
    score <= 1 ? '#ef4444' : score === 2 ? '#f59e0b' : score === 3 ? '#3b82f6' : '#22c55e'
  const label =
    score <= 1 ? 'Weak' : score === 2 ? 'Fair' : score === 3 ? 'Good' : 'Strong'

  if (!password) return null

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{ width: `${(score / 4) * 100}%`, backgroundColor: barColor }}
          />
        </div>
        <span className="text-xs font-medium" style={{ color: barColor }}>
          {label}
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1">
        {checks.map((c) => (
          <div key={c.label} className="flex items-center gap-1.5">
            <CheckCircle
              size={11}
              className={c.ok ? 'text-accent-green' : 'text-text-muted'}
            />
            <span className={`text-xs ${c.ok ? 'text-text-secondary' : 'text-text-muted'}`}>
              {c.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Register() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [company, setCompany] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState('Viewer')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [agreed, setAgreed] = useState(false)

  const handleStep1 = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!name.trim() || !email.trim() || !company.trim()) {
      setError('Please fill in all fields.')
      return
    }
    setStep(2)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (password !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters.')
      return
    }
    if (!agreed) {
      setError('Please accept the terms to continue.')
      return
    }

    setLoading(true)
    try {
      const res = await register({ name, email, password, company, role })
      setAuth(res.access_token, res.user)
      navigate('/')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Registration failed. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-lg">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-10 h-10 rounded-xl bg-accent-blue flex items-center justify-center shadow-lg shadow-accent-blue/30">
            <Zap size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-text-primary font-bold text-xl leading-none">Supply Chain</h1>
            <p className="text-accent-blue text-sm font-medium">Intelligence Platform</p>
          </div>
        </div>

        <div className="card p-8">
          {/* Step indicator */}
          <div className="flex items-center gap-3 mb-6">
            {[1, 2].map((s) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                    step >= s
                      ? 'bg-accent-blue text-white'
                      : 'bg-surface text-text-muted border border-border'
                  }`}
                >
                  {step > s ? <CheckCircle size={14} /> : s}
                </div>
                <span
                  className={`text-xs font-medium ${
                    step >= s ? 'text-text-primary' : 'text-text-muted'
                  }`}
                >
                  {s === 1 ? 'Your Info' : 'Security'}
                </span>
                {s < 2 && <ChevronRight size={14} className="text-text-muted" />}
              </div>
            ))}
          </div>

          <h2 className="text-text-primary font-semibold text-xl mb-1">Create your account</h2>
          <p className="text-text-secondary text-sm mb-6">
            {step === 1
              ? 'Tell us about yourself and your organization'
              : 'Set a secure password and choose your access level'}
          </p>

          {error && (
            <div className="flex items-center gap-2 bg-accent-red/10 border border-accent-red/30 rounded-lg px-3 py-2.5 mb-4">
              <AlertCircle size={16} className="text-accent-red shrink-0" />
              <p className="text-accent-red text-sm">{error}</p>
            </div>
          )}

          {/* Step 1 */}
          {step === 1 && (
            <form onSubmit={handleStep1} className="space-y-4">
              <div>
                <label className="block text-text-secondary text-sm mb-1.5">Full Name</label>
                <div className="relative">
                  <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="input pl-9"
                    placeholder="Jane Smith"
                    required
                    autoFocus
                  />
                </div>
              </div>

              <div>
                <label className="block text-text-secondary text-sm mb-1.5">Work Email</label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="input pl-9"
                    placeholder="jane@company.com"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-text-secondary text-sm mb-1.5">Company / Organization</label>
                <div className="relative">
                  <Building2 size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type="text"
                    value={company}
                    onChange={(e) => setCompany(e.target.value)}
                    className="input pl-9"
                    placeholder="Acme Logistics"
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary w-full py-2.5 flex items-center justify-center gap-2">
                Continue
                <ChevronRight size={16} />
              </button>
            </form>
          )}

          {/* Step 2 */}
          {step === 2 && (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-text-secondary text-sm mb-1.5">Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="input pl-9 pr-10"
                    placeholder="Create a strong password"
                    required
                    autoFocus
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                <PasswordStrength password={password} />
              </div>

              <div>
                <label className="block text-text-secondary text-sm mb-1.5">Confirm Password</label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                  <input
                    type={showConfirm ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="input pl-9 pr-10"
                    placeholder="Repeat your password"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirm(!showConfirm)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary"
                  >
                    {showConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
                {confirmPassword && password !== confirmPassword && (
                  <p className="text-accent-red text-xs mt-1">Passwords do not match</p>
                )}
                {confirmPassword && password === confirmPassword && (
                  <p className="text-accent-green text-xs mt-1 flex items-center gap-1">
                    <CheckCircle size={11} /> Passwords match
                  </p>
                )}
              </div>

              {/* Role selection */}
              <div>
                <label className="block text-text-secondary text-sm mb-2">Access Level</label>
                <div className="grid grid-cols-2 gap-2">
                  {ROLE_OPTIONS.map((r) => (
                    <button
                      key={r.value}
                      type="button"
                      onClick={() => setRole(r.value)}
                      className={`text-left p-3 rounded-xl border transition-all ${
                        role === r.value
                          ? 'border-accent-blue bg-accent-blue/10'
                          : 'border-border bg-surface hover:border-border/80'
                      }`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span
                          className="text-xs font-semibold px-1.5 py-0.5 rounded"
                          style={{ backgroundColor: r.color + '22', color: r.color }}
                        >
                          {r.label}
                        </span>
                        {role === r.value && (
                          <CheckCircle size={12} className="text-accent-blue ml-auto" />
                        )}
                      </div>
                      <p className="text-text-muted text-xs leading-snug">{r.description}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Terms */}
              <label className="flex items-start gap-3 cursor-pointer">
                <div className="relative mt-0.5">
                  <input
                    type="checkbox"
                    checked={agreed}
                    onChange={(e) => setAgreed(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-colors ${
                      agreed ? 'bg-accent-blue border-accent-blue' : 'border-border bg-surface'
                    }`}
                  >
                    {agreed && <CheckCircle size={10} className="text-white" />}
                  </div>
                </div>
                <span className="text-text-secondary text-sm leading-relaxed">
                  I agree to the{' '}
                  <span className="text-accent-blue hover:underline cursor-pointer">Terms of Service</span>{' '}
                  and{' '}
                  <span className="text-accent-blue hover:underline cursor-pointer">Privacy Policy</span>
                </span>
              </label>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => { setStep(1); setError('') }}
                  className="btn-secondary flex-1 py-2.5"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={loading || !agreed}
                  className="btn-primary flex-1 py-2.5 flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {loading && <LoadingSpinner size="sm" />}
                  Create Account
                </button>
              </div>
            </form>
          )}

          <div className="mt-5 pt-5 border-t border-border text-center">
            <p className="text-text-muted text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-accent-blue hover:underline font-medium">
                Sign in
              </Link>
            </p>
          </div>
        </div>

        <p className="text-center text-text-muted text-xs mt-4">
          Smart Supply Chain Optimization Platform v1.0
        </p>
      </div>
    </div>
  )
}
