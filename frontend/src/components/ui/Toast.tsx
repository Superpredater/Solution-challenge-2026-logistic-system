import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from 'lucide-react'
import { useUIStore } from '../../store/uiStore'
import clsx from 'clsx'

const ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  warning: AlertTriangle,
  info: Info,
}

const STYLES = {
  success: 'border-accent-green/30 bg-accent-green/10',
  error: 'border-accent-red/30 bg-accent-red/10',
  warning: 'border-accent-amber/30 bg-accent-amber/10',
  info: 'border-accent-blue/30 bg-accent-blue/10',
}

const ICON_STYLES = {
  success: 'text-accent-green',
  error: 'text-accent-red',
  warning: 'text-accent-amber',
  info: 'text-accent-blue',
}

export function ToastContainer() {
  const { toasts, removeToast } = useUIStore()

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((toast) => {
        const Icon = ICONS[toast.type]
        return (
          <div
            key={toast.id}
            className={clsx(
              'flex items-start gap-3 p-4 rounded-xl border backdrop-blur-sm shadow-lg',
              STYLES[toast.type]
            )}
          >
            <Icon size={18} className={clsx('mt-0.5 shrink-0', ICON_STYLES[toast.type])} />
            <div className="flex-1 min-w-0">
              <p className="text-text-primary font-medium text-sm">{toast.title}</p>
              {toast.message && (
                <p className="text-text-secondary text-xs mt-0.5">{toast.message}</p>
              )}
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              className="text-text-muted hover:text-text-primary transition-colors shrink-0"
            >
              <X size={14} />
            </button>
          </div>
        )
      })}
    </div>
  )
}
