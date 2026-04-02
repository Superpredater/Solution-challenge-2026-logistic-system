import { Component, type ReactNode } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: string }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: '' }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error: error.message }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex flex-col items-center justify-center h-64 gap-4 p-8">
          <div className="w-12 h-12 rounded-full bg-accent-red/20 flex items-center justify-center">
            <AlertTriangle size={24} className="text-accent-red" />
          </div>
          <div className="text-center">
            <p className="text-text-primary font-semibold mb-1">Something went wrong</p>
            <p className="text-text-muted text-sm max-w-md">{this.state.error}</p>
          </div>
          <button
            onClick={() => { this.setState({ hasError: false, error: '' }); window.location.reload() }}
            className="btn-secondary flex items-center gap-2"
          >
            <RefreshCw size={14} />
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
