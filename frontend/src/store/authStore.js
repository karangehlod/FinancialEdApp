import { create } from 'zustand'
import { authService } from '../services/apiService'
import tokenManager from '../utils/tokenManager'
import axios from 'axios'
import logger from '../utils/logger'

const API_HOST = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_BASE_URL = `${API_HOST}/api/v1`

export const useAuthStore = create((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,   // Start true so ProtectedRoute shows spinner until initAuth completes
  error: null,
  tokenTimeRemaining: null,
  sessionWarning: false,

  // Initialize auth state from localStorage — attempts token refresh if
  // the access token has expired but a valid refresh token still exists.
  initAuth: async () => {
    try {
      const token = tokenManager.getAccessToken()
      const refreshToken = tokenManager.getRefreshToken()
      const isValid = tokenManager.isTokenValid()
      
      if (token && isValid) {
        // Access token is still valid — fetch user data
        set({ isAuthenticated: true, isLoading: true })
        try {
          const user = await authService.getCurrentUser()
          set({ user, isLoading: false })
        } catch (error) {
          console.warn('Failed to fetch user during init:', error)
          set({ isLoading: false })
        }
        tokenManager.scheduleTokenRefresh()
        return true
      } else if (refreshToken) {
        // Access token expired or missing, but refresh token exists — try
        // to silently refresh the session so the user stays logged in
        // across page reloads.
        logger.info('Access token expired — attempting silent refresh…')
        set({ isLoading: true })
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          const { access_token, refresh_token: newRefresh } = response.data
          tokenManager.storeToken(access_token, newRefresh || refreshToken)

          // Fetch user data with the new token
          const user = await authService.getCurrentUser()
          set({ isAuthenticated: true, user, isLoading: false, error: null })
          tokenManager.scheduleTokenRefresh()
          logger.info('Silent token refresh succeeded')
          return true
        } catch (refreshError) {
          logger.warn('Silent token refresh failed — session expired', { error: String(refreshError) })
          tokenManager.clearTokens()
          set({ isAuthenticated: false, user: null, isLoading: false })
          return false
        }
      }
      
      // No tokens at all
      set({ isLoading: false, isAuthenticated: false })
      return false
    } catch (error) {
      logger.error('Error initializing auth:', { error: String(error) })
      set({ isLoading: false, isAuthenticated: false })
      return false
    }
  },

  // Register user
  register: async (userData) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.register(userData)
      set({ isLoading: false })
      return response
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Registration failed'
      set({ isLoading: false, error: errorMessage })
      throw error
    }
  },

  // Login user
  login: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.login(credentials)
      // Store tokens immediately so subsequent API calls (e.g., fetching user or
      // route data) have the Authorization header available and don't cause
      // transient 401s that redirect the app back to /login.
      if (response.access_token && response.refresh_token) {
        tokenManager.storeToken(response.access_token, response.refresh_token)
      }

      // Mark as authenticated immediately so router can proceed. Fetch user
      // data in background so transient failures don't prevent navigation.
      set({ isAuthenticated: true, isLoading: true, error: null, sessionWarning: false })

      // Background fetch for user data (do not block navigation)
      authService.getCurrentUser()
        .then((user) => set({ user, isLoading: false }))
        .catch((err) => {
          logger.warn('Background fetch of current user failed after login:', { error: String(err) })
          set({ isLoading: false })
        })

      // Schedule token refresh monitoring
      tokenManager.scheduleTokenRefresh()

      // Perform a hard redirect to dashboard to ensure the router and auth
      // state are synchronized and avoid route race conditions.
      try {
        window.location.replace('/dashboard')
      } catch (e) {
        // Fallback to client-side navigation if replace fails
      }

      return response
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Login failed'
      set({ isLoading: false, error: errorMessage })
      throw error
    }
  },

  // Logout user
  logout: () => {
    try {
      authService.logout()
    } catch (error) {
      logger.error('Error during logout API call:', { error: String(error) })
    }
    
    tokenManager.clearTokens()
    set({
      user: null,
      isAuthenticated: false,
      error: null,
      sessionWarning: false,
      tokenTimeRemaining: null,
    })
    // Ensure we always end up on the login page after logout — use hard
    // redirect to avoid race conditions where route guards may re-run.
    try {
      window.location.replace('/login')
    } catch (e) {
      // ignore in test envs
    }
  },

  // Get current user
  fetchCurrentUser: async () => {
    set({ isLoading: true })
    try {
      const user = await authService.getCurrentUser()
      set({ user, isLoading: false, isAuthenticated: true })
      // Schedule token refresh monitoring
      tokenManager.scheduleTokenRefresh()
      return user
    } catch (error) {
      logger.error('Failed to fetch current user:', { error: String(error) })
      
      // Check if token is still valid before clearing
      const isValid = tokenManager.isTokenValid()
      if (!isValid) {
        tokenManager.clearTokens()
        set({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          error: 'Session expired. Please log in again.',
        })
      } else {
        // Token is valid but user fetch failed (network error)
        set({
          isLoading: false,
          error: 'Failed to fetch user data',
        })
      }
      
      throw error
    }
  },

  // Update profile
  updateProfile: async (profileData) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.updateProfile(profileData)
      set({ user: response, isLoading: false })
      return response
    } catch (error) {
      const errorMessage = error.response?.data?.detail || 'Update failed'
      set({ isLoading: false, error: errorMessage })
      throw error
    }
  },

  // Update token time remaining (called periodically).
  // If the access token has expired, try a silent refresh before logging out.
  updateTokenStatus: () => {
    try {
      const timeRemaining = tokenManager.getTokenTimeRemaining()
      const isValid = tokenManager.isTokenValid()
      
      if (!isValid) {
        const refreshToken = tokenManager.getRefreshToken()
        if (refreshToken) {
          // Attempt silent refresh instead of immediate logout
          get().refreshSession()
        } else {
          get().logout()
        }
      }
      
      set({ tokenTimeRemaining: timeRemaining })
    } catch (error) {
      logger.error('Error updating token status:', { error: String(error) })
    }
  },

  // Show session warning
  showSessionWarning: () => {
    set({ sessionWarning: true })
  },

  // Dismiss session warning
  dismissSessionWarning: () => {
    set({ sessionWarning: false })
  },

  // Refresh token attempt
  refreshSession: async () => {
    try {
      const response = await authService.refreshToken()
      if (response.access_token && response.refresh_token) {
        tokenManager.storeToken(response.access_token, response.refresh_token)
        set({ sessionWarning: false })
        return true
      }
      return false
    } catch (error) {
      logger.error('Failed to refresh session:', { error: String(error) })
      // Force logout on refresh failure
      get().logout()
      return false
    }
  },

  // Get token status
  getTokenStatus: () => tokenManager.getTokenStatus(),

  // Clear error
  clearError: () => set({ error: null }),

  // Set user (for client-side updates)
  setUser: (user) => set({ user }),
}))
