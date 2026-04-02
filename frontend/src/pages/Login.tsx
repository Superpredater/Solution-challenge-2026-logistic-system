import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Zap, Eye, EyeOff, AlertCircle, ChevronRight, Shield, BarChart2, Package, Eye as EyeIcon } from 'lucide-react'
import { login, DEMO_ACCOUNTS } from '../api/auth'
import { useAuthStore } from '../store/authStore'
import { LoadingSpinner } from '../components/ui/LoadingSpinner'

const ROLE_ICONS: Record<string, React.ReactNode> = {
  Admin: <Shield size={14} />,
  Manager: <ChevronRight size={14} />,
  Analyst: <BarChart2 size={14} />,
  Viewer: <EyeIcon size={14} />,
}

export default function Login() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [mfaRequired, setMfaRequired] = useState(false)
  const [loading, setLoading] = useState(false)
  const [demoLoading, setDemoLoading] = useState<string | null>(null)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login({ email, password, totp_code: mfaRequired ? totpCode : undefined })
      if (res.mfa_required && !mfaRequired) {
        setMfaRequired(true)
        setLoading(false)
        return
      }
      setAuth(res.access_token, res.user)
      navigate('/')
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Invalid credentials. Please try again.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  const handleDemoLogin = async (demoEmail: string, demoPassword: string, demoId: string) => {
    setDemoLoading(demoId)
    setError('')
    try {
      const res = await login({ email: demoEmail, password: demoPassword })
      setAuth(res.access_token, res.user)
      navigate('/')
    } catch {
      setError('Demo login failed. Please try again.')
    } finally {
      setDemoLoading(null)
    }
  }

  return (
    <div className="min-h-screen bg-bg flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid grid-cols-1 lg:grid-cols-2 gap-6">

        {/* Left — Login form */}
        <div className="flex flex-col justify-center">
          {/* Logo */}
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-accent-blue flex items-center justify-center shadow-lg shadow-accent-blue/30">
              <Zap size={20} className="text-white" />
            </div>
            <div>
              <h1 className="text-text-primary font-bold text-xl leading-none">Supply Chain</h1>
              <p className="text-accent-blue text-sm font-medium">Intelligence Platform</p>
            </div>
          </div>

          <div className="card p-8">
            <h2 className="text-text-primary font-semibold text-xl mb-1">
              {mfaRequired ? 'Two-Factor Authentication' : 'Sign in'}
            </h2>
            <p className="text-text-secondary text-sm mb-6">
              {mfaRequired
                ? 'Enter the 6-digit code from your authenticator app'
                : 'Enter your credentials to access the platform'}
            </p>

            {error && (
              <div className="flex items-center gap-2 bg-accent-red/10 border border-accent-red/30 rounded-lg px-3 py-2.5 mb-4">
                <AlertCircle size={16} className="text-accent-red shrink-0" />
                <p className="text-accent-red text-sm">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {!mfaRequired ? (
                <>
                  <div>
                    <label className="block text-text-secondary text-sm mb-1.5">Email</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="input"
                      placeholder="you@company.com"
                      required
                      autoFocus
                    />
                  </div>
                  <div>
                    <label className="block text-text-secondary text-sm mb-1.5">Password</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="input pr-10"
                        placeholder="••••••••"
                        required
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </button>
                    </div>
                  </div>
                </>
              ) : (
                <div>
                  <label className="block text-text-secondary text-sm mb-1.5">Authenticator Code</label>
                  <input
                    type="text"
                    value={totpCode}
                    onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    className="input text-center text-2xl tracking-widest font-mono"
                    placeholder="000000"
                    maxLength={6}
                    autoFocus
                    required
                  />
                  <button
                    type="button"
                    onClick={() => { setMfaRequired(false); setTotpCode('') }}
                    className="text-accent-blue text-xs mt-2 hover:underline"
                  >
                    ← Back to login
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="btn-primary w-full flex items-center justify-center gap-2 py-2.5"
              >
                {loading && <LoadingSpinner size="sm" />}
                {mfaRequired ? 'Verify Code' : 'Sign In'}
              </button>
            </form>

            <div className="mt-5 pt-5 border-t border-border text-center">
              <p className="text-text-muted text-sm">
                Don't have an account?{' '}
                <Link to="/register" className="text-accent-blue hover:underline font-medium">
                  Create account
                </Link>
              </p>
            </div>
          </div>

          <p className="text-center text-text-muted text-xs mt-4">
            Smart Supply Chain Optimization Platform v1.0
          </p>
        </div>

        {/* Right — Demo accounts */}
        <div className="flex flex-col justify-center">
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-1">
              <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
              <h3 className="text-text-primary font-semibold">Demo Accounts</h3>
            </div>
            <p className="text-text-muted text-xs mb-5">
              Click any account to instantly sign in and explore the platform
            </p>

            <div className="space-y-3">
              {DEMO_ACCOUNTS.map((demo) => (
                <button
                  key={demo.id}
                  onClick={() => handleDemoLogin(demo.email, demo.password, demo.id)}
                  disabled={!!demoLoading}
                  className="w-full text-left p-4 rounded-xl border border-border bg-surface hover:border-accent-blue/50 hover:bg-card transition-all group disabled:opacity-60"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {/* Avatar */}
                      <div
                        className="w-9 h-9 rounded-full flex items-center justify-center text-white text-sm font-bold shrink-0"
                        style={{ backgroundColor: demo.color + '33', color: demo.color }}
                      >
                        {demo.name.charAt(0)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="text-text-primary text-sm font-medium">{demo.name}</p>
                          <span
                            className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium"
                            style={{ backgroundColor: demo.color + '22', color: demo.color }}
                          >
                            {ROLE_ICONS[demo.role]}
                            {demo.role}
                          </span>
                        </div>
                        <p className="text-text-muted text-xs mt-0.5">{demo.description}</p>
                      </div>
                    </div>
                    <div className="shrink-0 ml-2">
                      {demoLoading === demo.id ? (
                        <LoadingSpinner size="sm" />
                      ) : (
                        <ChevronRight
                          size={16}
                          className="text-text-muted group-hover:text-accent-blue transition-colors"
                        />
                      )}
                    </div>
                  </div>
                  {/* Credentials hint */}
                  <div className="mt-2 pt-2 border-t border-border/50 flex gap-4 text-xs text-text-muted font-mono">
                    <span>{demo.email}</span>
                    <span>demo1234</span>
                  </div>
                </button>
              ))}
            </div>

            <div className="mt-4 p-3 bg-accent-blue/10 border border-accent-blue/20 rounded-lg">
              <p className="text-accent-blue text-xs leading-relaxed">
                <strong>Note:</strong> Demo accounts work without a backend. All data shown is simulated.
                Connect the backend for live data.
              </p>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
