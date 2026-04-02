import { useEffect, useRef, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuthStore } from '../store/authStore'
import { useUIStore } from '../store/uiStore'

type WSMessage = {
  type: 'risk_score_update' | 'alert_created' | 'shipment_position_update'
  payload: Record<string, unknown>
}

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const queryClient = useQueryClient()
  const token = useAuthStore((s) => s.token)
  const addToast = useUIStore((s) => s.addToast)
  const incrementUnreadAlerts = useUIStore((s) => s.incrementUnreadAlerts)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (!token) return

    try {
      const wsUrl = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000')
      const ws = new WebSocket(`${wsUrl}/api/v1/ws?token=${token}`)
      wsRef.current = ws

      ws.onmessage = (event) => {
        try {
          const msg: WSMessage = JSON.parse(event.data)

          if (msg.type === 'risk_score_update') {
            const { shipment_id } = msg.payload as { shipment_id: string }
            queryClient.invalidateQueries({ queryKey: ['shipment', shipment_id] })
            queryClient.invalidateQueries({ queryKey: ['shipments'] })
          }

          if (msg.type === 'alert_created') {
            const alert = msg.payload as { severity: string; message: string }
            queryClient.invalidateQueries({ queryKey: ['alerts'] })
            incrementUnreadAlerts()
            if (alert.severity === 'Critical') {
              addToast({ type: 'error', title: 'Critical Alert', message: alert.message as string })
            }
          }

          if (msg.type === 'shipment_position_update') {
            queryClient.invalidateQueries({ queryKey: ['shipments'] })
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        // Retry after 10s — don't spam reconnects
        reconnectTimer.current = setTimeout(connect, 10_000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      // WebSocket not available — silently skip
    }
  }, [token, queryClient, addToast, incrementUnreadAlerts])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  return wsRef
}
