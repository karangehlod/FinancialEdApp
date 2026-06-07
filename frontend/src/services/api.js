import axios from 'axios'
import tokenManager from '../utils/tokenManager'
import logger from '../utils/logger'

const API_HOST = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_BASE_URL = `${API_HOST}/api/v1`

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor — attach token, never log token value in production
apiClient.interceptors.request.use(
  (config) => {
    const token = tokenManager.getAccessToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    // Only log in development and never include the token value
    logger.debug('API request', { method: config.method, url: config.url })
    return config
  },
  (error) => {
    logger.error('API request setup error', { error: error.message })
    return Promise.reject(error)
  }
)

// Response interceptor - handle token refresh and errors
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    // If 401 and not already retried, try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true

      try {
        const refreshToken = tokenManager.getRefreshToken()
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })

          const { access_token, refresh_token: newRefresh } = response.data
          tokenManager.storeToken(access_token, newRefresh || refreshToken)
          originalRequest.headers.Authorization = `Bearer ${access_token}`

          return apiClient(originalRequest)
        } else {
          // No refresh token, redirect to login
          tokenManager.clearTokens()
          window.location.href = '/login'
        }
      } catch (refreshError) {
        tokenManager.clearTokens()
        window.location.href = '/login'
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export default apiClient
