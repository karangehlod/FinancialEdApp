/**
 * useWebSocket — React hook for the real-time notification WebSocket.
 *
 * Features:
 *   - Auto-connects on mount (authenticated users only)
 *   - Auto-reconnects with exponential backoff on disconnect
 *   - Handles server ping/pong heartbeat
 *   - Dispatches notifications to the notification store (Zustand)
 *   - Cleans up on unmount
 *
 * Usage:
 *   const { isConnected, lastMessage } = useWebSocket();
 *
 * The hook automatically connects when the user has a valid access token.
 * Notifications received via WebSocket update the app's notification state
 * in real-time without polling.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store/authStore';
import logger from '../utils/logger';

// Exponential backoff settings
const INITIAL_RETRY_DELAY = 1000;     // 1 second
const MAX_RETRY_DELAY = 30000;        // 30 seconds
const MAX_RETRIES = 10;
const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

/**
 * @param {object} options
 * @param {function} options.onNotification - Callback for notification messages
 * @param {boolean} options.enabled - Whether to connect (default: true if authenticated)
 */
export function useWebSocket({ onNotification, enabled = true } = {}) {
  const { accessToken, isAuthenticated } = useAuthStore();
  const wsRef = useRef(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef(null);
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const [error, setError] = useState(null);

  const shouldConnect = enabled && isAuthenticated && !!accessToken;

  const handleMessage = useCallback((event) => {
    try {
      const msg = JSON.parse(event.data);
      setLastMessage(msg);

      switch (msg.type) {
        case 'connection_ack':
          console.debug('[WS] Connection acknowledged');
          break;

        case 'ping':
          // Respond with pong
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'pong' }));
          }
          break;

        case 'pong':
          // Server acknowledged our ping
          break;

        case 'budget_alert':
        case 'goal_milestone':
        case 'loan_reminder':
        case 'expense_added':
        case 'system_notice':
          // Deliver to notification handler
          if (onNotification) {
            onNotification(msg);
          }
          break;

        default:
          console.debug('[WS] Unknown message type:', msg.type);
      }
    } catch (err) {
      console.error('[WS] Failed to parse message:', err);
    }
  }, [onNotification]);

  const connect = useCallback(() => {
    if (!shouldConnect) return;

    // Don't reconnect if already open or connecting
    if (wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    // Use cookie-based authentication for WebSocket connections.
    // Rationale:
    //  - httpOnly, Secure cookies are not accessible to JavaScript and are
    //    automatically included in the WebSocket upgrade request by the
    //    browser for same-origin connections. This avoids exposing tokens in
    //    URLs or client-side logs.
    //  - Server must validate the session using the cookie (e.g., a session
    //    cookie or refresh token session) and reject unauthorized upgrades.
    // Requirements for the server:
    //  1. Set an httpOnly, Secure cookie (e.g. "session" or "refresh_token")
    //     on successful login with SameSite=None if cross-site embedding is
    //     needed. Prefer SameSite=Lax or Strict when possible.
    //  2. Accept and validate cookies during the WebSocket upgrade handshake
    //     and use that to authenticate the connection. Do NOT accept tokens
    //     via query string parameters.
    //  3. Reject connections with missing/invalid session cookie.
    //  4. Ensure origin checks are performed to prevent cross-site WebSocket
    //     abuse.

    const url = `${WS_BASE_URL}/ws/notifications`;
    let ws;
    try {
      // Create a plain WebSocket connection. The browser will attach cookies
      // automatically for same-origin requests. For cross-origin, ensure the
      // server sets the cookie with the appropriate domain and SameSite policy.
      ws = new WebSocket(url);
      logger.debug('[WS] Connecting to', { url })
    } catch (err) {
      logger.error('[WS] Failed to create WebSocket', { error: String(err) })
      setError('WebSocket creation failed')
      return
    }
    wsRef.current = ws;

    ws.onopen = () => {
      logger.debug('[WS] Connected')
      setIsConnected(true);
      setError(null);
      retryCountRef.current = 0;  // Reset retry counter on successful connect
    };

    ws.onmessage = handleMessage;

    ws.onclose = (event) => {
      logger.debug('[WS] Disconnected', { code: event.code, reason: event.reason })
      setIsConnected(false);
      wsRef.current = null;

      // Don't retry on intentional close or auth failures
      if (event.code === 1000 || event.code === 1008) return;

      // Exponential backoff retry
      if (retryCountRef.current < MAX_RETRIES && shouldConnect) {
        const delay = Math.min(
          INITIAL_RETRY_DELAY * 2 ** retryCountRef.current,
          MAX_RETRY_DELAY,
        );
        retryCountRef.current += 1;
        logger.debug(`[WS] Reconnecting in ${delay}ms (attempt ${retryCountRef.current})`);
        retryTimerRef.current = setTimeout(connect, delay);
      } else {
        setError('WebSocket connection lost. Real-time notifications unavailable.');
      }
    };

    ws.onerror = (err) => {
      logger.error('[WS] Error', { error: String(err) })
      setError('WebSocket connection error');
    };
  }, [shouldConnect, accessToken, handleMessage]);

  const disconnect = useCallback(() => {
    clearTimeout(retryTimerRef.current);
    if (wsRef.current) {
      wsRef.current.close(1000, 'Component unmounted');
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const sendMessage = useCallback((message) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    }
  }, []);

  useEffect(() => {
    if (shouldConnect) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [shouldConnect, connect, disconnect]);

  return {
    isConnected,
    lastMessage,
    error,
    sendMessage,
  };
}
