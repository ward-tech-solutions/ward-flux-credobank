import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export const useWebSocket = () => {
  const queryClient = useQueryClient()
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const ws = new WebSocket(`${protocol}//${window.location.host}/ws/updates`)

      ws.onopen = () => {
        console.log('✓ WebSocket connected')
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          if (data.type === 'status_change') {
            console.log('Device status changed:', data.changes)

            // Invalidate relevant queries to refetch data
            queryClient.invalidateQueries({ queryKey: ['devices'] })
            queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })

            // Show notification
            data.changes.forEach((change: any) => {
              const type = change.new_status === 'Up' ? 'success' : 'error'
              showNotification(
                `${change.hostname}: ${change.old_status} → ${change.new_status}`,
                type
              )
            })
          }
        } catch (error) {
          console.error('WebSocket message parse error:', error)
        }
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }

      ws.onclose = () => {
        console.log('WebSocket closed, reconnecting in 5s...')
        wsRef.current = null

        // Reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          connect()
        }, 5000)
      }

      wsRef.current = ws
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [queryClient])

  return wsRef.current
}

function showNotification(message: string, type: 'success' | 'error' | 'info' | 'warning') {
  // Create toast notification
  const toast = document.createElement('div')
  toast.className = `toast ${type}`

  const icon = type === 'success' ? '✓' : type === 'error' ? '✗' : 'ℹ'

  toast.innerHTML = `
    <div class="toast-icon">${icon}</div>
    <div class="toast-content">
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `

  let container = document.querySelector('.toast-container')
  if (!container) {
    container = document.createElement('div')
    container.className = 'toast-container'
    document.body.appendChild(container)
  }

  container.appendChild(toast)

  // Auto remove after 5 seconds
  setTimeout(() => {
    toast.remove()
  }, 5000)
}
