/**
 * Axios-based API client with typed request/response interceptors.
 * Handles automatic token attachment, refresh on 401, and centralized error handling.
 */

import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { API_BASE_URL } from '@/config/env'
import tokenManager from '@/utils/tokenManager'
import logger from '@/utils/logger'

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

// ── Request Interceptor ────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // Log non-sensitive request metadata without headers or token values
    logger.debug('API request', { method: config.method, url: config.url })
    return config
  },
  (error: unknown) => {
    const message = error instanceof Error ? error.message : 'Unknown request error'
    logger.error('API request setup error', { error: message })
    return Promise.reject(error)
  },
)

// ── Response Interceptor ───────────────────────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error)) return Promise.reject(error)

    const originalRequest = error.config as RetryableConfig | undefined
    if (!originalRequest) return Promise.reject(error)

    // 401 → attempt silent token refresh
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      const refreshToken = tokenManager.getRefreshToken()
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const data = response.data as { access_token: string; refresh_token?: string }
          tokenManager.storeToken(data.access_token, data.refresh_token ?? refreshToken)
          originalRequest.headers.Authorization = `Bearer ${data.access_token}`

          return apiClient(originalRequest)
        } catch {
          tokenManager.clearTokens()
          window.location.href = '/login'
          return Promise.reject(error)
        }
      } else {
        tokenManager.clearTokens()
        window.location.href = '/login'
      }
    }

    return Promise.reject(error)
  },
)

export default apiClient
