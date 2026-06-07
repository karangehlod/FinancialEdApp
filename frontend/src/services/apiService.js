import apiClient from './api'
import tokenManager from '../utils/tokenManager'

export const authService = {
  register: async (userData) => {
    const response = await apiClient.post('/auth/register', userData)
    return response.data
  },

  login: async (credentials) => {
    const response = await apiClient.post('/auth/login', credentials)
    const { access_token, refresh_token } = response.data
    tokenManager.storeToken(access_token, refresh_token)
    return response.data
  },

  logout: () => {
    tokenManager.clearTokens()
  },

  getCurrentUser: async () => {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  updateProfile: async (profileData) => {
    // logger.info('[authService] updateProfile called', { profileData })
    const response = await apiClient.put('/auth/profile', profileData)
    // logger.info('[authService] updateProfile response', { data: response.data })
    return response.data
  },

  updateFinancialProfile: async (financialData) => {
    const response = await apiClient.put('/auth/financial-profile', financialData)
    return response.data
  },

  getFinancialProfile: async () => {
    const response = await apiClient.get('/auth/financial-profile')
    return response.data
  },

  changePassword: async (passwordData) => {
    const response = await apiClient.post('/auth/change-password', passwordData)
    return response.data
  },

  /**
   * Exchange a refresh token for a new access + refresh token pair.
   * Used for silent session renewal on page reload or token expiry.
   */
  refreshToken: async () => {
    const refreshToken = tokenManager.getRefreshToken()
    if (!refreshToken) throw new Error('No refresh token available')
    const response = await apiClient.post('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },
}

export const expenseService = {
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/expenses', { params: filters })
    // API returns { expenses: [...], total, page, page_size }
    // Return just the array for compatibility with the store
    return response.data?.expenses || []
  },

  getOne: async (id) => {
    const response = await apiClient.get(`/expenses/${id}`)
    return response.data
  },

  create: async (expenseData) => {
    const response = await apiClient.post('/expenses', expenseData)
    return response.data
  },

  update: async (id, expenseData) => {
    const response = await apiClient.put(`/expenses/${id}`, expenseData)
    return response.data
  },

  delete: async (id) => {
    const response = await apiClient.delete(`/expenses/${id}`)
    return response.data
  },

  getAnalytics: async (filters = {}) => {
    const response = await apiClient.get('/expenses/analytics', { params: filters })
    return response.data
  },
}

export const budgetService = {
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/budgets', { params: filters })
    // API might return { data: [...] } or an array directly
    return response.data?.data || response.data?.budgets || response.data || []
  },

  getOne: async (id) => {
    const response = await apiClient.get(`/budgets/${id}`)
    return response.data
  },

  create: async (budgetData) => {
    const response = await apiClient.post('/budgets', budgetData)
    return response.data
  },

  update: async (id, budgetData) => {
    const response = await apiClient.put(`/budgets/${id}`, budgetData)
    return response.data
  },

  delete: async (id) => {
    const response = await apiClient.delete(`/budgets/${id}`)
    return response.data
  },

  getAlerts: async () => {
    const response = await apiClient.get('/budgets/alerts')
    return response.data
  },
}

export const loanService = {
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/loans', { params: filters })
    // API might return { data: [...] } or an array directly
    return response.data?.data || response.data?.loans || response.data || []
  },

  getOne: async (id) => {
    const response = await apiClient.get(`/loans/${id}`)
    return response.data
  },

  create: async (loanData) => {
    const response = await apiClient.post('/loans', loanData)
    return response.data
  },

  update: async (id, loanData) => {
    const response = await apiClient.put(`/loans/${id}`, loanData)
    return response.data
  },

  delete: async (id) => {
    const response = await apiClient.delete(`/loans/${id}`)
    return response.data
  },

  getSchedule: async (id) => {
    const response = await apiClient.get(`/loans/${id}/schedule`)
    return response.data
  },
}

export const goalService = {
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/goals', { params: filters })
    // API returns { success, data: [...], pagination }
    return response.data?.data || response.data?.goals || response.data || []
  },

  getOne: async (id) => {
    const response = await apiClient.get(`/goals/${id}`)
    return response.data
  },

  create: async (goalData) => {
    const response = await apiClient.post('/goals', goalData)
    return response.data
  },

  update: async (id, goalData) => {
    const response = await apiClient.put(`/goals/${id}`, goalData)
    return response.data
  },

  delete: async (id) => {
    const response = await apiClient.delete(`/goals/${id}`)
    return response.data
  },

  addProgress: async (id, amount) => {
    const response = await apiClient.put(`/goals/${id}/progress`, { current_amount: amount })
    return response.data
  },
}

export const notificationService = {
  getAll: async (filters = {}) => {
    const response = await apiClient.get('/notifications', { params: filters })
    return response.data
  },

  markAsRead: async (id) => {
    const response = await apiClient.put(`/notifications/${id}/read`)
    return response.data
  },

  delete: async (id) => {
    const response = await apiClient.delete(`/notifications/${id}`)
    return response.data
  },
}

export const exportService = {
  exportExpenses: async (format = 'csv', filters = {}) => {
    try {
      // Backend supports CSV and Excel. PDF will be converted to CSV server-side
      const endpoint = format === 'excel' ? '/exports/expenses/excel' : '/exports/expenses/csv'
      const response = await apiClient.post(endpoint, filters, {
        responseType: 'blob',
      })
      return response.data
    } catch (error) {
      console.error('Export expenses error:', error)
      throw error
    }
  },

  exportBudgets: async (format = 'csv', filters = {}) => {
    try {
      // Backend supports CSV. Excel format will default to CSV
      const endpoint = '/exports/budgets/csv'
      const response = await apiClient.post(endpoint, filters, {
        responseType: 'blob',
      })
      return response.data
    } catch (error) {
      console.error('Export budgets error:', error)
      throw error
    }
  },

  exportReport: async (format = 'csv', filters = {}) => {
    try {
      // Report export defaults to complete financial data in Excel if available, otherwise expenses CSV
      if (format === 'excel') {
        const response = await apiClient.post('/exports/complete/excel', filters, {
          responseType: 'blob',
        })
        return response.data
      }
      // Default to expenses export for CSV report
      return await exportService.exportExpenses('csv', filters)
    } catch (error) {
      console.error('Export report error:', error)
      // Fallback to expenses if complete export fails
      try {
        return await exportService.exportExpenses('csv', filters)
      } catch (fallbackError) {
        console.error('Export fallback error:', fallbackError)
        throw fallbackError
      }
    }
  },
}

// ── Two-Factor Authentication Service ────────────────────────────────────
export const twoFactorService = {
  /** Start 2FA setup — returns TOTP secret + provisioning URI for QR code */
  setup: async () => {
    const response = await apiClient.post('/auth/2fa/setup')
    return response.data
  },

  /** Confirm 2FA with the first TOTP code → returns backup codes */
  enable: async (code) => {
    const response = await apiClient.post('/auth/2fa/enable', { code })
    return response.data
  },

  /** Disable 2FA — requires password + current TOTP or backup code */
  disable: async (password, code) => {
    const response = await apiClient.post('/auth/2fa/disable', { password, code })
    return response.data
  },

  /** Verify TOTP during login (second factor step) */
  verify: async (userId, code) => {
    const response = await apiClient.post('/auth/2fa/verify', { user_id: userId, code })
    return response.data
  },

  /** Get new backup codes (invalidates old ones) */
  getBackupCodes: async () => {
    const response = await apiClient.get('/auth/2fa/backup-codes')
    return response.data
  },
}

// ── OAuth Service ────────────────────────────────────────────────────────
export const oauthService = {
  /** Get the list of linked OAuth providers for the current user */
  getLinkedProviders: async () => {
    const response = await apiClient.get('/auth/oauth/providers')
    return response.data
  },

  /** Unlink an OAuth provider */
  unlinkProvider: async (provider) => {
    const response = await apiClient.delete(`/auth/oauth/${provider}`)
    return response.data
  },
}

// ── Admin Service ────────────────────────────────────────────────────────
export const adminService = {
  /** Get paginated user list */
  getUsers: async (page = 1, perPage = 50, search = '', activeOnly = false) => {
    const params = { page, per_page: perPage }
    if (search) params.search = search
    if (activeOnly) params.active_only = activeOnly
    const response = await apiClient.get('/admin/users', { params })
    return response.data
  },

  /** Suspend or unsuspend a user */
  suspendUser: async (userId, suspended = true, reason = '') => {
    const response = await apiClient.post(`/admin/users/${userId}/suspend`, {
      suspended,
      reason,
    })
    return response.data
  },

  /** Get platform metrics summary */
  getMetrics: async () => {
    const response = await apiClient.get('/admin/metrics/summary')
    return response.data
  },

  /** Get audit log entries */
  getAuditLog: async (limit = 100) => {
    const response = await apiClient.get('/admin/audit-log', { params: { limit } })
    return response.data
  },

  /** Admin health check */
  getHealth: async () => {
    const response = await apiClient.get('/admin/health')
    return response.data
  },
}
