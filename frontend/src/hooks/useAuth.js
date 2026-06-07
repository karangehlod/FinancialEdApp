import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useProfileStore } from '../store/index'
import tokenManager from '../utils/tokenManager'

/**
 * Hook to protect routes - redirects to login if not authenticated
 */
export const useProtectedRoute = () => {
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
 * Hook to fetch and verify current user on app initialization
 * Note: This hook does NOT use useNavigate() as it runs before Router context
 */
export const useInitAuth = () => {
  const { isAuthenticated, initAuth, fetchCurrentUser, logout, showSessionWarning } = useAuthStore()
  const { fetchProfile, fetchFinancialProfile, setCurrency } = useProfileStore()

  useEffect(() => {
    const setupAuth = async () => {
      try {
        // Initialize auth state from localStorage
        // initAuth now handles token refresh automatically when the access
        // token has expired but a valid refresh token still exists.
        const authOk = await initAuth()
        
        // Check if we have a valid (possibly refreshed) token
        const token = tokenManager.getAccessToken()
        // Initialization debug removed for production. Use logger.debug if needed.
        
        if (authOk && token) {
           // Fetch both user profile and financial profile
          try {
            const profile = await fetchProfile()
            if (profile && profile.currency) {
              setCurrency(profile.currency)
            }
          } catch (error) {
            console.error('Failed to fetch profile:', error)
          }
          
          try {
            const financialProfile = await fetchFinancialProfile()
            if (financialProfile && financialProfile.currency) {
              setCurrency(financialProfile.currency)
            }
          } catch (error) {
            console.error('Failed to fetch financial profile:', error)
          }
        }
        // If initAuth returned false, the session is truly expired and the
        // user will be redirected by useProtectedRoute.
      } catch (error) {
        console.error('Init Auth - Setup failed:', error)
      }
    }

    setupAuth()

    // Set up token expiration callbacks
    tokenManager.setTokenCallbacks(
      // On token expired: call centralized logout which will redirect
      () => { logout() },
      // On token warning (5 minutes before expiry): show session warning
      () => { showSessionWarning() }
    )

    // Monitor token status every minute
    const tokenStatusInterval = setInterval(() => {
      try {
        const { updateTokenStatus } = useAuthStore.getState()
        updateTokenStatus()
      } catch (error) {
        console.error('Token status update failed:', error)
      }
    }, 60000) // Check every minute

    return () => {
      clearInterval(tokenStatusInterval)
      tokenManager.clearTokenTimers()
    }
  }, [])
}
