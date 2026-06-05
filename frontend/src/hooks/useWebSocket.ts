/**
 * WebSocket hook — real-time notifications with auto-reconnect.
 */

import { useEffect, useRef, useState, useCallback } from 'react'
import { useAuthStore } from '@/store/authStore'
import { env } from '@/config/env'
import logger from '@/utils/logger'
import type { WSMessage } from '@/types'

const INITIAL_RETRY_DELAY = 1_000
const MAX_RETRY_DELAY = 30_000
const MAX_RETRIES = 10

interface UseWebSocketOptions {
  readonly onNotification?: (msg: WSMessage) => void
  readonly enabled?: boolean
}

interface UseWebSocketReturn {
  readonly isConnected: boolean
  readonly lastMessage: WSMessage | null
  readonly error: string | null
  readonly sendMessage: (message: WSMessage) => void
}

export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const { onNotification, enabled = true } = options
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)

  const wsRef = useRef<WebSocket | null>(null)
  const retryCountRef = useRef(0)
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const [isConnected, setIsConnected] = useState(false)
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null)
  const [error, setError] = useState<string | null>(null)

  const shouldConnect = enabled && isAuthenticated

  const handleMessage = useCallback(
    (event: MessageEvent): void => {
      try {
        const msg = JSON.parse(event.data as string) as WSMessage
        setLastMessage(msg)

        switch (msg.type) {
          case 'connection_ack':
            logger.debug('[WS] Connection acknowledged')
            break
          case 'ping':
            if (wsRef.current?.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: 'pong' }))
            }
            break
          case 'pong':
            break
          case 'budget_alert':
          case 'goal_milestone':
          case 'loan_reminder':
          case 'expense_added':
          case 'system_notice':
            onNotification?.(msg)
            break
          default:
            logger.debug('[WS] Unknown message type', { type: msg.type })
        }
      } catch {
        logger.error('[WS] Failed to parse message')
      }
    },
    [onNotification],
  )

  const connect = useCallback((): void => {
    if (!shouldConnect) return
    if (
      wsRef.current?.readyState === WebSocket.OPEN ||
      wsRef.current?.readyState === WebSocket.CONNECTING
    ) {
      return
    }

    const url = `${env.wsUrl}/ws/notifications`
    let ws: WebSocket
    try {
      ws = new WebSocket(url)
      logger.debug('[WS] Connecting', { url })
    } catch (err) {
      logger.error('[WS] Failed to create WebSocket', { error: String(err) })
      setError('WebSocket creation failed')
      return
    }
    wsRef.current = ws

    ws.onopen = (): void => {
      logger.debug('[WS] Connected')
      setIsConnected(true)
      setError(null)
      retryCountRef.current = 0
    }

    ws.onmessage = handleMessage

    ws.onclose = (event): void => {
      logger.debug('[WS] Disconnected', { code: event.code, reason: event.reason })
      setIsConnected(false)
      wsRef.current = null

      if (event.code === 1000 || event.code === 1008) return

      if (retryCountRef.current < MAX_RETRIES && shouldConnect) {
        const delay = Math.min(INITIAL_RETRY_DELAY * 2 ** retryCountRef.current, MAX_RETRY_DELAY)
        retryCountRef.current += 1
        logger.debug(`[WS] Reconnecting in ${delay}ms (attempt ${retryCountRef.current})`)
        retryTimerRef.current = setTimeout(connect, delay)
      } else {
        setError('WebSocket connection lost. Real-time notifications unavailable.')
      }
    }

    ws.onerror = (): void => {
      logger.error('[WS] Error')
      setError('WebSocket connection error')
    }
  }, [shouldConnect, handleMessage])

  const disconnect = useCallback((): void => {
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current)
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounted')
      wsRef.current = null
    }
    setIsConnected(false)
  }, [])

  const sendMessage = useCallback((message: WSMessage): void => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message))
    }
  }, [])

  useEffect(() => {
    if (shouldConnect) {
      connect()
    } else {
      disconnect()
    }
    return disconnect
  }, [shouldConnect, connect, disconnect])

  return { isConnected, lastMessage, error, sendMessage }
}
