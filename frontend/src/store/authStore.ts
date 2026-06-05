/**
 * Auth Store — centralized authentication state management.
 * Handles login, logout, token refresh, and session lifecycle.
 */

import { create } from 'zustand'
import { authService } from '@/services/apiService'
import tokenManager from '@/utils/tokenManager'
import logger from '@/utils/logger'
import { API_BASE_URL } from '@/config/env'
import axios from 'axios'
import type { User, LoginCredentials, LoginResponse, RegisterData } from '@/types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  tokenTimeRemaining: number | null
  sessionWarning: boolean
}

interface AuthActions {
  initAuth: () => Promise<boolean>
  register: (data: RegisterData) => Promise<User>
  login: (credentials: LoginCredentials) => Promise<LoginResponse>
  logout: () => void
  fetchCurrentUser: () => Promise<User>
  updateProfile: (data: Partial<User>) => Promise<User>
  updateTokenStatus: () => void
  showSessionWarning: () => void
  dismissSessionWarning: () => void
  refreshSession: () => Promise<boolean>
  clearError: () => void
  setUser: (user: User) => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  tokenTimeRemaining: null,
  sessionWarning: false,

  initAuth: async () => {
    try {
      const token = tokenManager.getAccessToken()
      const refreshToken = tokenManager.getRefreshToken()
      const isValid = tokenManager.isTokenValid()

      if (token && isValid) {
        set({ isAuthenticated: true, isLoading: true })
        try {
          const user = await authService.getCurrentUser()
          set({ user, isLoading: false })
        } catch {
          set({ isLoading: false })
        }
        tokenManager.scheduleTokenRefresh()
        return true
      } else if (refreshToken) {
        logger.info('Access token expired — attempting silent refresh…')
        set({ isLoading: true })
        try {
          const response = await axios.post<{ access_token: string; refresh_token?: string }>(
            `${API_BASE_URL}/auth/refresh`,
            { refresh_token: refreshToken },
          )
          const { access_token, refresh_token: newRefresh } = response.data
          tokenManager.storeToken(access_token, newRefresh ?? refreshToken)

          const user = await authService.getCurrentUser()
          set({ isAuthenticated: true, user, isLoading: false, error: null })
          tokenManager.scheduleTokenRefresh()
          logger.info('Silent token refresh succeeded')
          return true
        } catch {
          logger.warn('Silent token refresh failed — session expired')
          tokenManager.clearTokens()
          set({ isAuthenticated: false, user: null, isLoading: false })
          return false
        }
      }

      set({ isLoading: false, isAuthenticated: false })
      return false
    } catch (error) {
      logger.error('Error initializing auth:', { error: String(error) })
      set({ isLoading: false, isAuthenticated: false })
      return false
    }
  },

  register: async (userData) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.register(userData)
      set({ isLoading: false })
      return response
    } catch (error) {
      const message = getErrorMessage(error, 'Registration failed')
      set({ isLoading: false, error: message })
      throw error
    }
  },

  login: async (credentials) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.login(credentials)

      if (response.access_token && response.refresh_token) {
        tokenManager.storeToken(response.access_token, response.refresh_token)
      }

      set({ isAuthenticated: true, isLoading: true, error: null, sessionWarning: false })

      // Background user fetch — don't block navigation
      authService
        .getCurrentUser()
        .then((user) => set({ user, isLoading: false }))
        .catch(() => set({ isLoading: false }))

      tokenManager.scheduleTokenRefresh()
      return response
    } catch (error) {
      const message = getErrorMessage(error, 'Login failed')
      set({ isLoading: false, error: message })
      throw error
    }
  },

  logout: () => {
    try {
      authService.logout()
    } catch {
      // Swallow
    }

    tokenManager.clearTokens()
    set({
      user: null,
      isAuthenticated: false,
      error: null,
      sessionWarning: false,
      tokenTimeRemaining: null,
    })

    try {
      window.location.replace('/login')
    } catch {
      // Ignore in test environments
    }
  },

  fetchCurrentUser: async () => {
    set({ isLoading: true })
    try {
      const user = await authService.getCurrentUser()
      set({ user, isLoading: false, isAuthenticated: true })
      tokenManager.scheduleTokenRefresh()
      return user
    } catch (error) {
      if (!tokenManager.isTokenValid()) {
        tokenManager.clearTokens()
        set({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          error: 'Session expired. Please log in again.',
        })
      } else {
        set({ isLoading: false, error: 'Failed to fetch user data' })
      }
      throw error
    }
  },

  updateProfile: async (profileData) => {
    set({ isLoading: true, error: null })
    try {
      const response = await authService.updateProfile(profileData)
      set({ user: response, isLoading: false })
      return response
    } catch (error) {
      const message = getErrorMessage(error, 'Update failed')
      set({ isLoading: false, error: message })
      throw error
    }
  },

  updateTokenStatus: () => {
    const timeRemaining = tokenManager.getTokenTimeRemaining()
    const isValid = tokenManager.isTokenValid()

    if (!isValid) {
      const refreshToken = tokenManager.getRefreshToken()
      if (refreshToken) {
        void get().refreshSession()
      } else {
        get().logout()
      }
    }

    set({ tokenTimeRemaining: timeRemaining })
  },

  showSessionWarning: () => set({ sessionWarning: true }),
  dismissSessionWarning: () => set({ sessionWarning: false }),

  refreshSession: async () => {
    try {
      const response = await authService.refreshToken()
      if (response.access_token && response.refresh_token) {
        tokenManager.storeToken(response.access_token, response.refresh_token)
        set({ sessionWarning: false })
        return true
      }
      return false
    } catch {
      logger.error('Failed to refresh session')
      get().logout()
      return false
    }
  },

  clearError: () => set({ error: null }),
  setUser: (user) => set({ user }),
}))

// ── Helpers ────────────────────────────────────────────────────────────

function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data as { detail?: string } | undefined
    return detail?.detail ?? fallback
  }
  return error instanceof Error ? error.message : fallback
}
