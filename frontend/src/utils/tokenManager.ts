/**
 * Token Manager — handles secure token lifecycle, storage, and expiration.
 * Uses localStorage with prefixed keys. Never exposes raw token values.
 */

const TOKEN_EXPIRATION_TIME = 3600 * 1000 // 1 hour
const REFRESH_WARNING_TIME = 5 * 60 * 1000 // 5 min before expiry
const STORAGE_PREFIX = 'fin_ed_'

let tokenRefreshTimer: ReturnType<typeof setTimeout> | null = null
let tokenWarningTimer: ReturnType<typeof setTimeout> | null = null
let onTokenExpired: (() => void) | null = null
let onTokenWarning: (() => void) | null = null

// ── Helpers ────────────────────────────────────────────────────────────

const key = (k: string): string => `${STORAGE_PREFIX}${k}`

function safeGetItem(k: string): string | null {
  try {
    return localStorage.getItem(key(k))
  } catch {
    return null
  }
}

function safeSetItem(k: string, value: string): void {
  try {
    localStorage.setItem(key(k), value)
  } catch {
    // Swallow — storage may be full or unavailable
  }
}

function safeRemoveItem(k: string): void {
  try {
    localStorage.removeItem(key(k))
  } catch {
    // Swallow
  }
}

// ── Public API ─────────────────────────────────────────────────────────

export function setTokenCallbacks(
  onExpired: (() => void) | null,
  onWarning: (() => void) | null,
): void {
  onTokenExpired = onExpired
  onTokenWarning = onWarning
}

export function storeToken(accessToken: string, refreshToken: string): boolean {
  if (!accessToken || !refreshToken) return false

  const expirationTime = Date.now() + TOKEN_EXPIRATION_TIME
  safeSetItem('access_token', accessToken)
  safeSetItem('refresh_token', refreshToken)
  safeSetItem('token_expiration', expirationTime.toString())
  safeSetItem('token_issued_at', Date.now().toString())
  safeSetItem('session_valid', 'true')

  scheduleTokenRefresh()
  return true
}

export function getTokenTimeRemaining(): number {
  const raw = safeGetItem('token_expiration')
  if (!raw) return 0
  const expiration = parseInt(raw, 10)
  if (isNaN(expiration)) return 0
  return Math.max(0, expiration - Date.now())
}

export function isTokenValid(): boolean {
  const raw = safeGetItem('token_expiration')
  if (!raw) return false
  const expiration = parseInt(raw, 10)
  if (isNaN(expiration)) return false
  const valid = Date.now() < expiration
  safeSetItem('session_valid', valid ? 'true' : 'false')
  return valid
}

export function shouldRefreshToken(): boolean {
  const remaining = getTokenTimeRemaining()
  return remaining < REFRESH_WARNING_TIME && remaining > 0
}

export function getTokenExpirationTime(): Date | null {
  const raw = safeGetItem('token_expiration')
  if (!raw) return null
  const ts = parseInt(raw, 10)
  return isNaN(ts) ? null : new Date(ts)
}

export function formatTokenTimeRemaining(): string {
  const remaining = getTokenTimeRemaining()
  if (remaining <= 0) return 'Expired'
  const minutes = Math.floor(remaining / 60000)
  const seconds = Math.floor((remaining % 60000) / 1000)
  return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`
}

export function clearTokenTimers(): void {
  if (tokenRefreshTimer) {
    clearTimeout(tokenRefreshTimer)
    tokenRefreshTimer = null
  }
  if (tokenWarningTimer) {
    clearTimeout(tokenWarningTimer)
    tokenWarningTimer = null
  }
}

export function scheduleTokenRefresh(): void {
  clearTokenTimers()

  const remaining = getTokenTimeRemaining()
  if (remaining <= 0) {
    onTokenExpired?.()
    return
  }

  const warningTime = Math.max(0, remaining - REFRESH_WARNING_TIME)
  if (warningTime > 0) {
    tokenWarningTimer = setTimeout(() => {
      onTokenWarning?.()
    }, warningTime)
  }

  tokenRefreshTimer = setTimeout(() => {
    onTokenExpired?.()
  }, remaining)
}

export function clearTokens(): void {
  safeRemoveItem('access_token')
  safeRemoveItem('refresh_token')
  safeRemoveItem('token_expiration')
  safeRemoveItem('token_issued_at')
  safeRemoveItem('session_valid')
  clearTokenTimers()
}

export function getAccessToken(): string | null {
  return safeGetItem('access_token')
}

export function getRefreshToken(): string | null {
  return safeGetItem('refresh_token')
}

export function updateTokenExpiration(): void {
  const expirationTime = Date.now() + TOKEN_EXPIRATION_TIME
  safeSetItem('token_expiration', expirationTime.toString())
  safeSetItem('session_valid', 'true')
  scheduleTokenRefresh()
}

export interface TokenStatus {
  readonly hasAccessToken: boolean
  readonly hasRefreshToken: boolean
  readonly isValid: boolean
  readonly timeRemaining: string
  readonly expiresAt: Date | null
  readonly shouldRefresh: boolean
  readonly sessionValid: boolean
}

export function getTokenStatus(): TokenStatus {
  return {
    hasAccessToken: !!getAccessToken(),
    hasRefreshToken: !!getRefreshToken(),
    isValid: isTokenValid(),
    timeRemaining: formatTokenTimeRemaining(),
    expiresAt: getTokenExpirationTime(),
    shouldRefresh: shouldRefreshToken(),
    sessionValid: safeGetItem('session_valid') === 'true',
  }
}

const tokenManager = {
  storeToken,
  getTokenTimeRemaining,
  isTokenValid,
  shouldRefreshToken,
  getTokenExpirationTime,
  formatTokenTimeRemaining,
  scheduleTokenRefresh,
  clearTokenTimers,
  clearTokens,
  getAccessToken,
  getRefreshToken,
  updateTokenExpiration,
  getTokenStatus,
  setTokenCallbacks,
} as const

export default tokenManager
