/**
 * Core domain types for the Financial Education application.
 * All types are strictly typed with no `any` usage.
 */

// ── User & Auth ────────────────────────────────────────────────────────

export interface User {
  readonly id: number
  readonly email: string
  readonly name: string | null
  readonly first_name: string | null
  readonly last_name: string | null
  readonly is_active: boolean
  readonly is_verified: boolean
  readonly two_factor_enabled: boolean
  readonly created_at: string
  readonly updated_at: string
  readonly currency: string | null
}

export interface LoginCredentials {
  readonly email: string
  readonly password: string
}

export interface RegisterData {
  readonly email: string
  readonly password: string
  readonly first_name: string
  readonly last_name: string
}

export interface AuthTokens {
  readonly access_token: string
  readonly refresh_token: string
  readonly token_type: string
}

export interface LoginResponse extends AuthTokens {
  readonly requires_2fa?: boolean
  readonly user_id?: number
  readonly user?: User
}

export interface TwoFactorSetupResponse {
  readonly secret: string
  readonly provisioning_uri: string
}

export interface TwoFactorEnableResponse {
  readonly backup_codes: readonly string[]
}

export interface TwoFactorVerifyResponse {
  readonly verified: boolean
  readonly access_token?: string
  readonly refresh_token?: string
}

// ── Financial Profile ──────────────────────────────────────────────────

export interface FinancialProfile {
  readonly id: number
  readonly user_id: number
  readonly monthly_salary: number | null
  readonly monthly_rent: number | null
  readonly monthly_insurance: number | null
  readonly currency: string
  readonly created_at: string
  readonly updated_at: string
}

// ── Expenses ───────────────────────────────────────────────────────────

export type ExpenseCategory =
  | 'food'
  | 'transport'
  | 'utilities'
  | 'entertainment'
  | 'health'
  | 'education'
  | 'shopping'
  | 'other'

export interface Expense {
  readonly id: number
  readonly user_id: number
  readonly amount: number
  readonly description: string
  readonly category: ExpenseCategory
  readonly date: string
  readonly created_at: string
  readonly updated_at: string
}

export interface ExpenseCreateData {
  readonly amount: number
  readonly description: string
  readonly category: ExpenseCategory
  readonly date: string
}

export interface ExpenseFilters {
  readonly category?: ExpenseCategory
  readonly start_date?: string
  readonly end_date?: string
  readonly page?: number
  readonly page_size?: number
}

// ── Budgets ────────────────────────────────────────────────────────────

export interface Budget {
  readonly id: number
  readonly user_id: number
  readonly category: string
  readonly amount: number
  readonly spent: number
  readonly month: number
  readonly year: number
  readonly created_at: string
  readonly updated_at: string
}

export interface BudgetCreateData {
  readonly category: string
  readonly amount: number
  readonly month: number
  readonly year: number
}

export interface BudgetFilters {
  readonly month?: number
  readonly year?: number
  readonly category?: string
}

// ── Goals ──────────────────────────────────────────────────────────────

export type GoalStatus = 'active' | 'completed' | 'paused' | 'cancelled'

export interface Goal {
  readonly id: number
  readonly user_id: number
  readonly title: string
  readonly description: string | null
  readonly target_amount: number
  readonly current_amount: number
  readonly deadline: string | null
  readonly status: GoalStatus
  readonly created_at: string
  readonly updated_at: string
}

export interface GoalCreateData {
  readonly title: string
  readonly description?: string
  readonly target_amount: number
  readonly current_amount?: number
  readonly deadline?: string
}

export interface GoalFilters {
  readonly status?: GoalStatus
}

// ── Loans ──────────────────────────────────────────────────────────────

export type LoanStatus = 'active' | 'paid_off' | 'defaulted'

export interface Loan {
  readonly id: number
  readonly user_id: number
  readonly name: string
  readonly principal: number
  readonly interest_rate: number
  readonly term_months: number
  readonly monthly_payment: number
  readonly remaining_balance: number
  readonly status: LoanStatus
  readonly start_date: string
  readonly created_at: string
  readonly updated_at: string
}

export interface LoanCreateData {
  readonly name: string
  readonly principal: number
  readonly interest_rate: number
  readonly term_months: number
  readonly start_date: string
}

export interface LoanScheduleEntry {
  readonly month: number
  readonly payment: number
  readonly principal: number
  readonly interest: number
  readonly balance: number
}

export interface LoanFilters {
  readonly status?: LoanStatus
}

// ── Notifications ──────────────────────────────────────────────────────

export type NotificationType =
  | 'budget_alert'
  | 'goal_milestone'
  | 'loan_reminder'
  | 'expense_added'
  | 'system_notice'

export interface Notification {
  readonly id: number
  readonly user_id: number
  readonly title: string
  readonly message: string
  readonly type: NotificationType
  readonly read: boolean
  readonly created_at: string
}

// ── WebSocket Messages ─────────────────────────────────────────────────

export type WSMessageType =
  | 'connection_ack'
  | 'ping'
  | 'pong'
  | NotificationType

export interface WSMessage {
  readonly type: WSMessageType
  readonly data?: Record<string, unknown>
}

// ── Admin ──────────────────────────────────────────────────────────────

export interface AdminUserList {
  readonly users: readonly User[]
  readonly total: number
  readonly page: number
  readonly per_page: number
}

export interface PlatformMetrics {
  readonly total_users: number
  readonly active_users: number
  readonly total_expenses: number
  readonly total_budgets: number
  readonly total_goals: number
}

export interface AuditLogEntry {
  readonly id: number
  readonly user_id: number
  readonly action: string
  readonly details: string
  readonly created_at: string
}

// ── API Response Wrappers ──────────────────────────────────────────────

export interface PaginatedResponse<T> {
  readonly data: readonly T[]
  readonly total: number
  readonly page: number
  readonly page_size: number
}

export interface ApiError {
  readonly detail: string
  readonly status_code?: number
}

// ── OAuth ──────────────────────────────────────────────────────────────

export type OAuthProvider = 'google' | 'apple'

export interface OAuthAuthorizeResponse {
  readonly auth_url: string
  readonly state: string
}

export interface OAuthCallbackPayload {
  readonly code: string
  readonly state: string
  readonly redirect_uri?: string
  readonly id_token?: string
  readonly user?: string
}

// ── Export Formats ──────────────────────────────────────────────────────

export type ExportFormat = 'csv' | 'excel'

// ── Theme ──────────────────────────────────────────────────────────────

export type Theme = 'light' | 'dark' | 'system'

// ── UI Component Types ─────────────────────────────────────────────────

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'outline'
export type ButtonSize = 'sm' | 'md' | 'lg'
export type BadgeVariant = 'primary' | 'secondary' | 'success' | 'warning' | 'danger'
export type IconSize = 'sm' | 'md' | 'lg'
