import { useCallback, useEffect, useRef, useState } from 'react'

export type ConnectionState = 'connecting' | 'open' | 'reconnecting' | 'closed' | 'error'

interface UseResilientWebSocketOptions {
  protocols?: string | string[]
  autoReconnect?: boolean
  reconnectBaseDelay?: number
  reconnectMaxDelay?: number
  reconnectFactor?: number
  jitter?: number
  heartbeatInterval?: number
  heartbeatTimeout?: number
  onOpen?: (event: Event) => void
  onClose?: (event: CloseEvent) => void
  onError?: (event: Event) => void
  onMessage?: (event: MessageEvent) => void
}

interface UseResilientWebSocketReturn {
  state: ConnectionState
  reconnectAttempts: number
  lastError: Event | null
}

const DEFAULTS = {
  autoReconnect: true,
  reconnectBaseDelay: 2000,
  reconnectMaxDelay: 60000,
  reconnectFactor: 1.5,
  jitter: 0.5,
  heartbeatInterval: 15000,
  heartbeatTimeout: 45000,
}

export function useResilientWebSocket(url: string | null, options: UseResilientWebSocketOptions = {}): UseResilientWebSocketReturn {
  const {
    protocols,
    autoReconnect = DEFAULTS.autoReconnect,
    reconnectBaseDelay = DEFAULTS.reconnectBaseDelay,
    reconnectMaxDelay = DEFAULTS.reconnectMaxDelay,
    reconnectFactor = DEFAULTS.reconnectFactor,
    jitter = DEFAULTS.jitter,
    heartbeatInterval = DEFAULTS.heartbeatInterval,
    heartbeatTimeout = DEFAULTS.heartbeatTimeout,
    onOpen,
    onClose,
    onError,
    onMessage,
  } = options

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | null>(null)
  const heartbeatIntervalRef = useRef<number | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const manualCloseRef = useRef(false)
  const lastHeartbeatRef = useRef<number>(Date.now())
  const handlersRef = useRef({ onOpen, onClose, onError, onMessage })

  useEffect(() => {
    handlersRef.current = { onOpen, onClose, onError, onMessage }
  }, [onOpen, onClose, onError, onMessage])

  const [state, setState] = useState<ConnectionState>('closed')
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastError, setLastError] = useState<Event | null>(null)

  const clearHeartbeat = () => {
    if (heartbeatIntervalRef.current) {
      window.clearInterval(heartbeatIntervalRef.current)
      heartbeatIntervalRef.current = null
    }
  }

  const scheduleReconnect = useCallback(() => {
    if (!autoReconnect || manualCloseRef.current) return

    const attempts = reconnectAttemptsRef.current + 1
    reconnectAttemptsRef.current = attempts
    setReconnectAttempts(attempts)

    const delay = Math.min(reconnectMaxDelay, reconnectBaseDelay * Math.pow(reconnectFactor, attempts - 1))
    const jitterOffset = delay * jitter * (Math.random() - 0.5) * 2
    const nextDelay = Math.max(1000, delay + jitterOffset)

    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current)
    }

    reconnectTimeoutRef.current = window.setTimeout(() => {
      setState('reconnecting')
      connect()
    }, nextDelay)
  }, [autoReconnect, reconnectBaseDelay, reconnectFactor, reconnectMaxDelay, jitter])

  const connect = useCallback(() => {
    if (!url) return

    const existing = wsRef.current
    if (existing) {
      const { readyState } = existing
      const hasWebSocketGlobals = typeof WebSocket !== 'undefined'
      const isConnectingOrOpen =
        (hasWebSocketGlobals && (readyState === WebSocket.OPEN || readyState === WebSocket.CONNECTING)) ||
        readyState === 0 ||
        readyState === 1
      if (isConnectingOrOpen) {
        return
      }
    }

    try {
      const socket = new WebSocket(url, protocols)
      wsRef.current = socket
      setState(reconnectAttemptsRef.current > 0 ? 'reconnecting' : 'connecting')

      socket.onopen = (event) => {
        reconnectAttemptsRef.current = 0
        setReconnectAttempts(0)
        setState('open')
        lastHeartbeatRef.current = Date.now()
        if (reconnectTimeoutRef.current) {
          window.clearTimeout(reconnectTimeoutRef.current)
          reconnectTimeoutRef.current = null
        }

        handlersRef.current.onOpen?.(event)

        clearHeartbeat()
        heartbeatIntervalRef.current = window.setInterval(() => {
          if (!wsRef.current) return
          const diff = Date.now() - lastHeartbeatRef.current
          if (diff > heartbeatTimeout) {
            wsRef.current.close()
          } else {
            wsRef.current.send(JSON.stringify({ type: 'pong', timestamp: Date.now() }))
          }
        }, heartbeatInterval)
      }

      socket.onmessage = (event) => {
        lastHeartbeatRef.current = Date.now()
        handlersRef.current.onMessage?.(event)
      }

      socket.onerror = (event) => {
        setLastError(event)
        setState('error')
        handlersRef.current.onError?.(event)
      }

      socket.onclose = (event) => {
        setState('closed')
        handlersRef.current.onClose?.(event)
        clearHeartbeat()
        wsRef.current = null
        if (!manualCloseRef.current) {
          scheduleReconnect()
        }
      }
    } catch (error) {
      setState('error')
      if (error instanceof Event) {
        setLastError(error)
        handlersRef.current.onError?.(error)
      }
      scheduleReconnect()
    }
  }, [url, protocols, heartbeatInterval, heartbeatTimeout, scheduleReconnect])

  useEffect(() => {
    manualCloseRef.current = false

    if (url) {
      connect()
    }

    return () => {
      manualCloseRef.current = true
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
      clearHeartbeat()
      const socket = wsRef.current
      if (socket) {
        wsRef.current = null

        socket.onopen = null
        socket.onmessage = null
        socket.onerror = null
        socket.onclose = null

        const hasWebSocketGlobals = typeof WebSocket !== 'undefined'
        const readyState = socket.readyState
        const isConnecting = hasWebSocketGlobals
          ? readyState === WebSocket.CONNECTING
          : readyState === 0

        if (isConnecting) {
          const closeWhenReady = () => {
            try {
              socket.close()
            } catch (_error) {
              /* no-op: socket already closed */
            }
          }

          socket.addEventListener('open', closeWhenReady, { once: true })
          socket.addEventListener('error', closeWhenReady, { once: true })
        } else {
          try {
            socket.close()
          } catch (_error) {
            /* no-op: socket already closed */
          }
        }
      }
    }
  }, [connect, url])

  return { state, reconnectAttempts, lastError }
}
