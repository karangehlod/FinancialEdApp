/**
 * Typed API service layer — centralised data-fetching abstraction.
 * Each service object maps to a backend domain entity.
 */

import apiClient from './api'
import tokenManager from '@/utils/tokenManager'
import type {
  User,
  LoginCredentials,
  LoginResponse,
  RegisterData,
  AuthTokens,
  FinancialProfile,
  Expense,
  ExpenseCreateData,
  ExpenseFilters,
  Budget,
  BudgetCreateData,
  BudgetFilters,
  Goal,
  GoalCreateData,
  GoalFilters,
  Loan,
  LoanCreateData,
  LoanFilters,
  LoanScheduleEntry,
  Notification,
  TwoFactorSetupResponse,
  TwoFactorEnableResponse,
  TwoFactorVerifyResponse,
  AdminUserList,
  PlatformMetrics,
  AuditLogEntry,
} from '@/types'

// ── Auth ───────────────────────────────────────────────────────────────

export const authService = {
  async register(userData: RegisterData): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', userData)
    return response.data
  },

  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await apiClient.post<LoginResponse>('/auth/login', credentials)
    const { access_token, refresh_token } = response.data
    if (access_token && refresh_token) {
      tokenManager.storeToken(access_token, refresh_token)
    }
    return response.data
  },

  logout(): void {
    tokenManager.clearTokens()
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  async updateProfile(profileData: Partial<User>): Promise<User> {
    const response = await apiClient.put<User>('/auth/profile', profileData)
    return response.data
  },

  async updateFinancialProfile(data: Partial<FinancialProfile>): Promise<FinancialProfile> {
    const response = await apiClient.put<FinancialProfile>('/auth/financial-profile', data)
    return response.data
  },

  async getFinancialProfile(): Promise<FinancialProfile> {
    const response = await apiClient.get<FinancialProfile>('/auth/financial-profile')
    return response.data
  },

  async changePassword(passwordData: { current_password: string; new_password: string }): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>('/auth/change-password', passwordData)
    return response.data
  },

  async refreshToken(): Promise<AuthTokens> {
    const refreshToken = tokenManager.getRefreshToken()
    if (!refreshToken) throw new Error('No refresh token available')
    const response = await apiClient.post<AuthTokens>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },
} as const

// ── Expenses ───────────────────────────────────────────────────────────

export const expenseService = {
  async getAll(filters: ExpenseFilters = {}): Promise<readonly Expense[]> {
    const response = await apiClient.get<{ expenses: Expense[] }>('/expenses', { params: filters })
    return response.data?.expenses ?? []
  },

  async getOne(id: number): Promise<Expense> {
    const response = await apiClient.get<Expense>(`/expenses/${id}`)
    return response.data
  },

  async create(data: ExpenseCreateData): Promise<Expense> {
    const response = await apiClient.post<Expense>('/expenses', data)
    return response.data
  },

  async update(id: number, data: Partial<ExpenseCreateData>): Promise<Expense> {
    const response = await apiClient.put<Expense>(`/expenses/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/expenses/${id}`)
  },

  async getAnalytics(filters: ExpenseFilters = {}): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>('/expenses/analytics', { params: filters })
    return response.data
  },
} as const

// ── Budgets ────────────────────────────────────────────────────────────

export const budgetService = {
  async getAll(filters: BudgetFilters = {}): Promise<readonly Budget[]> {
    const response = await apiClient.get<{ data?: Budget[]; budgets?: Budget[] } | Budget[]>('/budgets', { params: filters })
    const d = response.data
    if (Array.isArray(d)) return d
    return (d as { data?: Budget[]; budgets?: Budget[] }).data ?? (d as { budgets?: Budget[] }).budgets ?? []
  },

  async getOne(id: number): Promise<Budget> {
    const response = await apiClient.get<Budget>(`/budgets/${id}`)
    return response.data
  },

  async create(data: BudgetCreateData): Promise<Budget> {
    const response = await apiClient.post<Budget>('/budgets', data)
    return response.data
  },

  async update(id: number, data: Partial<BudgetCreateData>): Promise<Budget> {
    const response = await apiClient.put<Budget>(`/budgets/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/budgets/${id}`)
  },

  async getAlerts(): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>('/budgets/alerts')
    return response.data
  },
} as const

// ── Loans ──────────────────────────────────────────────────────────────

export const loanService = {
  async getAll(filters: LoanFilters = {}): Promise<readonly Loan[]> {
    const response = await apiClient.get<{ data?: Loan[]; loans?: Loan[] } | Loan[]>('/loans', { params: filters })
    const d = response.data
    if (Array.isArray(d)) return d
    return (d as { data?: Loan[]; loans?: Loan[] }).data ?? (d as { loans?: Loan[] }).loans ?? []
  },

  async getOne(id: number): Promise<Loan> {
    const response = await apiClient.get<Loan>(`/loans/${id}`)
    return response.data
  },

  async create(data: LoanCreateData): Promise<Loan> {
    const response = await apiClient.post<Loan>('/loans', data)
    return response.data
  },

  async update(id: number, data: Partial<LoanCreateData>): Promise<Loan> {
    const response = await apiClient.put<Loan>(`/loans/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/loans/${id}`)
  },

  async getSchedule(id: number): Promise<readonly LoanScheduleEntry[]> {
    const response = await apiClient.get<readonly LoanScheduleEntry[]>(`/loans/${id}/schedule`)
    return response.data
  },
} as const

// ── Goals ──────────────────────────────────────────────────────────────

export const goalService = {
  async getAll(filters: GoalFilters = {}): Promise<readonly Goal[]> {
    const response = await apiClient.get<{ data?: Goal[]; goals?: Goal[] } | Goal[]>('/goals', { params: filters })
    const d = response.data
    if (Array.isArray(d)) return d
    return (d as { data?: Goal[]; goals?: Goal[] }).data ?? (d as { goals?: Goal[] }).goals ?? []
  },

  async getOne(id: number): Promise<Goal> {
    const response = await apiClient.get<Goal>(`/goals/${id}`)
    return response.data
  },

  async create(data: GoalCreateData): Promise<Goal> {
    const response = await apiClient.post<Goal>('/goals', data)
    return response.data
  },

  async update(id: number, data: Partial<GoalCreateData>): Promise<Goal> {
    const response = await apiClient.put<Goal>(`/goals/${id}`, data)
    return response.data
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/goals/${id}`)
  },

  async addProgress(id: number, amount: number): Promise<Goal> {
    const response = await apiClient.put<Goal>(`/goals/${id}/progress`, { current_amount: amount })
    return response.data
  },
} as const

// ── Notifications ──────────────────────────────────────────────────────

export const notificationService = {
  async getAll(filters: Record<string, unknown> = {}): Promise<readonly Notification[]> {
    const response = await apiClient.get<readonly Notification[]>('/notifications', { params: filters })
    return response.data
  },

  async markAsRead(id: number): Promise<void> {
    await apiClient.put(`/notifications/${id}/read`)
  },

  async delete(id: number): Promise<void> {
    await apiClient.delete(`/notifications/${id}`)
  },
} as const

// ── Two-Factor Authentication ──────────────────────────────────────────

export const twoFactorService = {
  async setup(): Promise<TwoFactorSetupResponse> {
    const response = await apiClient.post<TwoFactorSetupResponse>('/auth/2fa/setup')
    return response.data
  },

  async enable(code: string): Promise<TwoFactorEnableResponse> {
    const response = await apiClient.post<TwoFactorEnableResponse>('/auth/2fa/enable', { code })
    return response.data
  },

  async disable(password: string, code: string): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>('/auth/2fa/disable', { password, code })
    return response.data
  },

  async verify(userId: number, code: string): Promise<TwoFactorVerifyResponse> {
    const response = await apiClient.post<TwoFactorVerifyResponse>('/auth/2fa/verify', { user_id: userId, code })
    return response.data
  },

  async getBackupCodes(): Promise<{ backup_codes: readonly string[] }> {
    const response = await apiClient.get<{ backup_codes: readonly string[] }>('/auth/2fa/backup-codes')
    return response.data
  },
} as const

// ── OAuth ──────────────────────────────────────────────────────────────

export const oauthService = {
  async getLinkedProviders(): Promise<readonly string[]> {
    const response = await apiClient.get<readonly string[]>('/auth/oauth/providers')
    return response.data
  },

  async unlinkProvider(provider: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(`/auth/oauth/${provider}`)
    return response.data
  },
} as const

// ── Export ──────────────────────────────────────────────────────────────

export const exportService = {
  async exportExpenses(format: 'csv' | 'excel' = 'csv', filters: Record<string, unknown> = {}): Promise<Blob> {
    const endpoint = format === 'excel' ? '/exports/expenses/excel' : '/exports/expenses/csv'
    const response = await apiClient.post<Blob>(endpoint, filters, { responseType: 'blob' })
    return response.data
  },

  async exportBudgets(filters: Record<string, unknown> = {}): Promise<Blob> {
    const response = await apiClient.post<Blob>('/exports/budgets/csv', filters, { responseType: 'blob' })
    return response.data
  },

  async exportReport(format: 'csv' | 'excel' = 'csv', filters: Record<string, unknown> = {}): Promise<Blob> {
    if (format === 'excel') {
      try {
        const response = await apiClient.post<Blob>('/exports/complete/excel', filters, { responseType: 'blob' })
        return response.data
      } catch {
        return exportService.exportExpenses('csv', filters)
      }
    }
    return exportService.exportExpenses('csv', filters)
  },
} as const

// ── Admin ──────────────────────────────────────────────────────────────

export const adminService = {
  async getUsers(page = 1, perPage = 50, search = '', activeOnly = false): Promise<AdminUserList> {
    const params: Record<string, unknown> = { page, per_page: perPage }
    if (search) params['search'] = search
    if (activeOnly) params['active_only'] = activeOnly
    const response = await apiClient.get<AdminUserList>('/admin/users', { params })
    return response.data
  },

  async suspendUser(userId: number, suspended = true, reason = ''): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(`/admin/users/${userId}/suspend`, { suspended, reason })
    return response.data
  },

  async getMetrics(): Promise<PlatformMetrics> {
    const response = await apiClient.get<PlatformMetrics>('/admin/metrics/summary')
    return response.data
  },

  async getAuditLog(limit = 100): Promise<readonly AuditLogEntry[]> {
    const response = await apiClient.get<readonly AuditLogEntry[]>('/admin/audit-log', { params: { limit } })
    return response.data
  },

  async getHealth(): Promise<Record<string, unknown>> {
    const response = await apiClient.get<Record<string, unknown>>('/admin/health')
    return response.data
  },
} as const
