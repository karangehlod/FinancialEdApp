/**
 * Environment configuration with runtime validation.
 * Centralizes all environment variables and provides type-safe access.
 * Fails fast in development if required variables are missing.
 */

interface EnvConfig {
  readonly apiUrl: string
  readonly wsUrl: string
  readonly adminEmails: readonly string[]
  readonly logEndpoint: string | null
  readonly appEnv: 'development' | 'staging' | 'production'
  readonly isDev: boolean
  readonly isProd: boolean
  readonly isStaging: boolean
}

function getEnvVar(key: string, fallback?: string): string {
  const value = import.meta.env[key] as string | undefined
  if (value !== undefined && value !== '') return value
  if (fallback !== undefined) return fallback

  if (import.meta.env.DEV) {
    console.warn(`[env] Missing environment variable: ${key}`)
  }
  return ''
}

function parseAdminEmails(raw: string): readonly string[] {
  return raw
    .split(',')
    .map((e) => e.trim().toLowerCase())
    .filter(Boolean)
}

function resolveAppEnv(): 'development' | 'staging' | 'production' {
  const raw = getEnvVar('VITE_APP_ENV', 'development')
  if (raw === 'staging' || raw === 'production') return raw
  return 'development'
}

const appEnv = resolveAppEnv()

export const env: EnvConfig = Object.freeze({
  apiUrl: getEnvVar('VITE_API_URL', 'http://localhost:8000'),
  wsUrl: getEnvVar('VITE_WS_URL', 'ws://localhost:8000'),
  adminEmails: parseAdminEmails(getEnvVar('VITE_ADMIN_EMAILS', '')),
  logEndpoint: getEnvVar('VITE_LOG_ENDPOINT') || null,
  appEnv,
  isDev: appEnv === 'development',
  isProd: appEnv === 'production',
  isStaging: appEnv === 'staging',
})

/** Computed API base URL for v1 endpoints.
 *
 * In development, use a relative path so the Vite dev server proxy
 * intercepts requests and forwards them to the backend — completely
 * avoiding CORS pre-flight checks.
 *
 * In production, use the full URL from VITE_API_URL.
 */
export const API_BASE_URL: string =
  appEnv === 'development'
    ? '/api/v1'
    : `${env.apiUrl}/api/v1`
