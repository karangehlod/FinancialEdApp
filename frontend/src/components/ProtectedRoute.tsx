/**
 * ProtectedRoute — guards routes requiring authentication with optional RBAC.
 *
 * Features:
 *   - Blocks unauthenticated access and redirects to /login
 *   - Supports role-based access control via `allowedRoles` prop
 *   - Waits for auth initialization before rendering (prevents flash)
 *   - Uses token validity check as secondary guard during hydration
 */

import { type ReactNode, memo } from 'react'
import { Navigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import tokenManager from '@/utils/tokenManager'
import { LoadingSpinner } from '@/components/UI'

// ── Types ──────────────────────────────────────────────────────────────

type UserRole = 'admin' | 'user'

interface ProtectedRouteProps {
  readonly children: ReactNode
  /** Restrict access to specific roles (checks against admin email list if 'admin'). */
  readonly allowedRoles?: readonly UserRole[]
}

// ── Loading Fallback ───────────────────────────────────────────────────

function AuthLoadingFallback(): JSX.Element {
  return (
    <div
      className="flex items-center justify-center min-h-[60vh] sm:min-h-screen"
      role="status"
      aria-label="Authenticating"
    >
      <LoadingSpinner size="md" />
    </div>
  )
}

// ── Access Denied ──────────────────────────────────────────────────────

function AccessDenied(): JSX.Element {
  return (
    <div
      className="flex flex-col items-center justify-center min-h-[60vh] sm:min-h-screen text-center px-4"
      role="alert"
    >
      <h1 className="text-2xl-fluid font-bold text-gray-900 dark:text-gray-100 mb-2">
        Access Denied
      </h1>
      <p className="text-gray-600 dark:text-gray-400 mb-6">
        You do not have permission to view this page.
      </p>
      <a
        href="/dashboard"
        className="text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300 font-medium underline"
      >
        Return to Dashboard
      </a>
    </div>
  )
}

// ── Helpers ─────────────────────────────────────────────────────────────

function isAdminUser(email: string | undefined | null): boolean {
  if (!email) return false
  const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS as string | undefined ?? '')
    .split(',')
    .map((e: string) => e.trim().toLowerCase())
    .filter(Boolean)
  return adminEmails.includes(email.toLowerCase())
}

// ── Component ──────────────────────────────────────────────────────────

export const ProtectedRoute = memo<ProtectedRouteProps>(function ProtectedRoute({
  children,
  allowedRoles,
}) {
  const { isAuthenticated, isLoading, user } = useAuthStore()

  // 1. Still initializing auth — show loading
  if (isLoading) {
    return <AuthLoadingFallback />
  }

  // 2. Token exists but store not yet populated — also wait
  const token = tokenManager.getAccessToken()
  if (!isAuthenticated && token && tokenManager.isTokenValid()) {
    return <AuthLoadingFallback />
  }

  // 3. Not authenticated — redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  // 4. RBAC check
  if (allowedRoles && allowedRoles.length > 0) {
    const userRoles: UserRole[] = isAdminUser(user?.email) ? ['admin', 'user'] : ['user']
    const hasRole = allowedRoles.some((role) => userRoles.includes(role))
    if (!hasRole) {
      return <AccessDenied />
    }
  }

  return <>{children}</>
})

export default ProtectedRoute
