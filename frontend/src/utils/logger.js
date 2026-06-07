/**
 * Environment-aware logger for the frontend.
 *
 * - In development: logs to console at the appropriate level
 * - In production:  suppresses debug/info logs; errors are sent to a
 *                   monitoring sink (configurable via VITE_LOG_ENDPOINT)
 *
 * NEVER log sensitive values (tokens, passwords, PII) — this module
 * enforces that by design: callers pass structured metadata, not raw strings.
 */

const IS_DEV = import.meta.env.DEV === true
const LOG_ENDPOINT = import.meta.env.VITE_LOG_ENDPOINT || null

const LEVELS = /** @type {const} */ ({
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
})

/** Minimum level to emit in the current environment. */
const MIN_LEVEL = IS_DEV ? LEVELS.debug : LEVELS.warn

/**
 * Strip any fields that look like credentials from a metadata object.
 * Acts as a safety net — callers should never pass sensitive data at all.
 *
 * @param {Record<string, unknown>} meta
 * @returns {Record<string, unknown>}
 */
function sanitize(meta) {
  if (!meta || typeof meta !== 'object') return {}
  const SENSITIVE_KEYS = /token|password|secret|key|credential|auth|bearer/i
  return Object.fromEntries(
    Object.entries(meta).filter(([k]) => !SENSITIVE_KEYS.test(k))
  )
}

/**
 * Send a log entry to the remote monitoring endpoint (production only).
 *
 * @param {'error' | 'warn'} level
 * @param {string} message
 * @param {Record<string, unknown>} meta
 */
async function sendToRemote(level, message, meta) {
  if (!LOG_ENDPOINT) return
  try {
    await fetch(LOG_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        level,
        message,
        meta: sanitize(meta),
        timestamp: new Date().toISOString(),
        url: window.location.pathname,
        userAgent: navigator.userAgent,
      }),
      keepalive: true,
    })
  } catch {
    // Never throw from the logger — swallow network errors silently
  }
}

/**
 * Core log function.
 *
 * @param {number} levelValue
 * @param {'debug' | 'info' | 'warn' | 'error'} levelName
 * @param {string} message
 * @param {Record<string, unknown>} [meta]
 */
function log(levelValue, levelName, message, meta = {}) {
  if (levelValue < MIN_LEVEL) return

  const clean = sanitize(meta)
  const consoleFn = console[levelName] || console.log

  if (IS_DEV) {
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
  } else if (levelValue >= LEVELS.error) {
    // In production only emit errors + warnings to console
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
    sendToRemote(levelName, message, clean)
  } else if (levelValue >= LEVELS.warn) {
    consoleFn(`[${levelName.toUpperCase()}] ${message}`, clean)
  }
}

const logger = {
  debug: (msg, meta) => log(LEVELS.debug, 'debug', msg, meta),
  info:  (msg, meta) => log(LEVELS.info,  'info',  msg, meta),
  warn:  (msg, meta) => log(LEVELS.warn,  'warn',  msg, meta),
  error: (msg, meta) => log(LEVELS.error, 'error', msg, meta),
}

export default logger
