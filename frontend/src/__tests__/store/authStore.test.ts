/**
 * authStore — unit tests.
 * Verifies login, logout, initAuth, and session state transitions.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useAuthStore } from '@/store/authStore'
import tokenManager from '@/utils/tokenManager'

// ── Mock apiService ────────────────────────────────────────────────────────

vi.mock('@/services/apiService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    register: vi.fn(),
    getCurrentUser: vi.fn(),
    refreshToken: vi.fn(),
    updateProfile: vi.fn(),
  },
}))

vi.mock('@/utils/tokenManager', () => ({
  default: {
    getAccessToken: vi.fn(() => null),
    getRefreshToken: vi.fn(() => null),
    isTokenValid: vi.fn(() => false),
    storeToken: vi.fn(() => true),
    clearTokens: vi.fn(),
    scheduleTokenRefresh: vi.fn(),
    clearTokenTimers: vi.fn(),
    setTokenCallbacks: vi.fn(),
    getTokenStatus: vi.fn(() => ({ hasAccessToken: false, isValid: false })),
  },
}))

import { authService } from '@/services/apiService'
const mockAuthService = authService as unknown as Record<string, ReturnType<typeof vi.fn>>

// ── Helpers ────────────────────────────────────────────────────────────────

const resetStore = () =>
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    isLoading: false,
    error: null,
    sessionWarning: false,
    tokenTimeRemaining: null,
  })

// ── Tests ──────────────────────────────────────────────────────────────────

describe('authStore', () => {
  beforeEach(() => {
    resetStore()
    vi.clearAllMocks()
  })

  // ── login ────────────────────────────────────────────────────────────────

  describe('login', () => {
    it('sets isAuthenticated on success', async () => {
      const mockUser = { id: 'user-1', email: 'test@example.com', name: 'Test User' }
      mockAuthService.login.mockResolvedValueOnce({
        access_token: 'tok_access',
        refresh_token: 'tok_refresh',
        token_type: 'bearer',
      })
      mockAuthService.getCurrentUser.mockResolvedValueOnce(mockUser)

      await useAuthStore.getState().login({ email: 'test@example.com', password: 'pw' })

      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })

    it('stores tokens on successful login', async () => {
      mockAuthService.login.mockResolvedValueOnce({
        access_token: 'tok_access',
        refresh_token: 'tok_refresh',
        token_type: 'bearer',
      })
      mockAuthService.getCurrentUser.mockResolvedValueOnce({ id: 'u1', email: 'a@b.com' })

      await useAuthStore.getState().login({ email: 'a@b.com', password: 'pw' })

      expect(tokenManager.storeToken).toHaveBeenCalledWith('tok_access', 'tok_refresh')
    })

    it('sets error and throws on failure', async () => {
      mockAuthService.login.mockRejectedValueOnce(new Error('Invalid credentials'))

      await expect(
        useAuthStore.getState().login({ email: 'bad@example.com', password: 'wrong' }),
      ).rejects.toThrow()

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().error).toBeTruthy()
    })
  })

  // ── logout ───────────────────────────────────────────────────────────────

  describe('logout', () => {
    it('clears auth state', () => {
      useAuthStore.setState({ isAuthenticated: true, user: { id: 'u1' } as any })
      mockAuthService.logout.mockResolvedValueOnce(undefined)

      useAuthStore.getState().logout()

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('clears tokens', () => {
      useAuthStore.getState().logout()
      expect(tokenManager.clearTokens).toHaveBeenCalled()
    })
  })

  // ── initAuth — no token ───────────────────────────────────────────────────

  describe('initAuth', () => {
    it('returns false when no token stored', async () => {
      vi.mocked(tokenManager.getAccessToken).mockReturnValue(null)
      vi.mocked(tokenManager.getRefreshToken).mockReturnValue(null)

      const result = await useAuthStore.getState().initAuth()

      expect(result).toBe(false)
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('returns true and fetches user with valid token', async () => {
      vi.mocked(tokenManager.getAccessToken).mockReturnValue('valid_token')
      vi.mocked(tokenManager.isTokenValid).mockReturnValue(true)
      const mockUser = { id: 'u1', email: 'x@y.com' }
      mockAuthService.getCurrentUser.mockResolvedValueOnce(mockUser)

      const result = await useAuthStore.getState().initAuth()

      expect(result).toBe(true)
    })
  })

  // ── clearError ────────────────────────────────────────────────────────────

  describe('clearError', () => {
    it('resets error to null', () => {
      useAuthStore.setState({ error: 'some error' })
      useAuthStore.getState().clearError()
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})
