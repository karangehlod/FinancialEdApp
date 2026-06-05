/**
 * Production-safe, environment-aware logger.
 *
 * - Development: all levels to console
 * - Production: only warn/error; errors forwarded to remote endpoint
 *
 * NEVER log sensitive values (tokens, passwords, PII).
 */

import { env } from '@/config/env'

const LEVELS = { debug: 0, info: 1, warn: 2, error: 3 } as const
type LogLevel = keyof typeof LEVELS
type LogMeta = Record<string, unknown>

const MIN_LEVEL = env.isDev ? LEVELS.debug : LEVELS.warn

const SENSITIVE_KEYS = /token|password|secret|key|credential|auth|bearer/i

function sanitize(meta: LogMeta): LogMeta {
  if (!meta || typeof meta !== 'object') return {}
  return Object.fromEntries(
    Object.entries(meta).filter(([k]) => !SENSITIVE_KEYS.test(k)),
  )
}

async function sendToRemote(level: LogLevel, message: string, meta: LogMeta): Promise<void> {
  if (!env.logEndpoint) return
  try {
    await fetch(env.logEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level,
        message,
        meta: sanitize(meta),
        timestamp: new Date().toISOString(),
        url: globalThis.location?.pathname ?? '',
        userAgent: globalThis.navigator?.userAgent ?? '',
      }),
      keepalive: true,
    })
  } catch {
    // Never throw from the logger — swallow network errors
  }
}

function log(levelValue: number, levelName: LogLevel, message: string, meta: LogMeta = {}): void {
  if (levelValue < MIN_LEVEL) return

  const clean = sanitize(meta)
  const consoleFn = console[levelName] ?? console.log

  if (env.isDev) {
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
  } else if (levelValue >= LEVELS.error) {
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
    void sendToRemote(levelName, message, clean)
  } else if (levelValue >= LEVELS.warn) {
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
  }
}

export const logger = {
  debug: (msg: string, meta?: LogMeta): void => log(LEVELS.debug, 'debug', msg, meta),
  info: (msg: string, meta?: LogMeta): void => log(LEVELS.info, 'info', msg, meta),
  warn: (msg: string, meta?: LogMeta): void => log(LEVELS.warn, 'warn', msg, meta),
  error: (msg: string, meta?: LogMeta): void => log(LEVELS.error, 'error', msg, meta),
} as const

export default logger
