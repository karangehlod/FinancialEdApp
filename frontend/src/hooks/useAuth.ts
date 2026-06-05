/**
 * Auth hooks — app-level authentication lifecycle.
 */

import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { useProfileStore } from '@/store/index'
import tokenManager from '@/utils/tokenManager'

/**
 * Redirect to /login when not authenticated.
 */
export function useProtectedRoute(): { isAuthenticated: boolean; isLoading: boolean } {
  const navigate = useNavigate()
  const { isAuthenticated, isLoading } = useAuthStore()

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate('/login', { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate])

  return { isAuthenticated, isLoading }
}

/**
 * Bootstrap auth state on mount — runs once at app startup.
 * Must execute before Router context (no useNavigate).
 */
export function useInitAuth(): void {
  const initAuth = useAuthStore((s) => s.initAuth)
  const logout = useAuthStore((s) => s.logout)
  const showSessionWarning = useAuthStore((s) => s.showSessionWarning)
  const { fetchProfile, fetchFinancialProfile, setCurrency } = useProfileStore()

  useEffect(() => {
    const setupAuth = async (): Promise<void> => {
      try {
        const authOk = await initAuth()
        const token = tokenManager.getAccessToken()

        if (authOk && token) {
          try {
            const profile = await fetchProfile()
            if (profile?.currency) setCurrency(profile.currency)
          } catch {
            // Non-critical
          }

          try {
            const fp = await fetchFinancialProfile()
            if (fp?.currency) setCurrency(fp.currency)
          } catch {
            // Non-critical
          }
        }
      } catch {
        // Auth init failed — user stays on login
      }
    }

    void setupAuth()

    tokenManager.setTokenCallbacks(
      () => logout(),
      () => showSessionWarning(),
    )

    const tokenStatusInterval = setInterval(() => {
      const { updateTokenStatus } = useAuthStore.getState()
      updateTokenStatus()
    }, 60_000)

    return () => {
      clearInterval(tokenStatusInterval)
      tokenManager.clearTokenTimers()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
