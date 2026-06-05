/**
 * Domain stores — feature-specific Zustand stores.
 * Each store encapsulates data fetching and state for one domain entity.
 */

import { create } from 'zustand'
import {
  expenseService,
  budgetService,
  loanService,
  goalService,
  notificationService,
  authService,
} from '@/services/apiService'
import type {
  User,
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
  Notification,
} from '@/types'

// ── Profile Store ──────────────────────────────────────────────────────

interface ProfileState {
  profile: User | null
  financialProfile: FinancialProfile | null
  isLoading: boolean
  error: string | null
  currency: string
}

interface ProfileActions {
  updateProfile: (data: Partial<User>) => Promise<User>
  updateFinancialProfile: (data: Partial<FinancialProfile>) => Promise<FinancialProfile>
  fetchProfile: () => Promise<User | undefined>
  fetchFinancialProfile: () => Promise<FinancialProfile | undefined>
  setCurrency: (currency: string) => void
  clearError: () => void
}

export const useProfileStore = create<ProfileState & ProfileActions>((set) => ({
  profile: null,
  financialProfile: null,
  isLoading: false,
  error: null,
  currency: 'USD',

  updateProfile: async (profileData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await authService.updateProfile(profileData)
      set({ profile: updated, currency: updated.currency ?? 'USD', isLoading: false })
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update profile' })
      throw new Error('Failed to update profile')
    }
  },

  updateFinancialProfile: async (financialData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await authService.updateFinancialProfile(financialData)
      set({ financialProfile: updated, currency: updated.currency ?? 'USD', isLoading: false })
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update financial profile' })
      throw new Error('Failed to update financial profile')
    }
  },

  fetchProfile: async () => {
    set({ isLoading: true, error: null })
    try {
      const user = await authService.getCurrentUser()
      set({ profile: user, isLoading: false })
      return user
    } catch {
      set({ isLoading: false, error: 'Failed to fetch profile' })
      return undefined
    }
  },

  fetchFinancialProfile: async () => {
    set({ isLoading: true, error: null })
    try {
      const fp = await authService.getFinancialProfile()
      set({ financialProfile: fp, currency: fp.currency ?? 'USD', isLoading: false })
      return fp
    } catch (error) {
      const status = (error as { response?: { status?: number } })?.response?.status
      if (status === 404) {
        set({ isLoading: false, financialProfile: null })
      } else {
        set({ isLoading: false, error: 'Failed to fetch financial profile' })
      }
      return undefined
    }
  },

  setCurrency: (currency) => set({ currency }),
  clearError: () => set({ error: null }),
}))

// ── Expenses Store ─────────────────────────────────────────────────────

interface ExpenseState {
  expenses: readonly Expense[]
  isLoading: boolean
  error: string | null
  currentExpense: Expense | null
}

interface ExpenseActions {
  fetchExpenses: (filters?: ExpenseFilters) => Promise<void>
  getExpense: (id: number) => Promise<Expense>
  createExpense: (data: ExpenseCreateData) => Promise<Expense>
  updateExpense: (id: number, data: Partial<ExpenseCreateData>) => Promise<Expense>
  deleteExpense: (id: number) => Promise<void>
  clearError: () => void
}

export const useExpenseStore = create<ExpenseState & ExpenseActions>((set) => ({
  expenses: [],
  isLoading: false,
  error: null,
  currentExpense: null,

  fetchExpenses: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await expenseService.getAll(filters)
      // Normalize expenses: ensure amount is number and date is ISO string
      const normalized = (data || []).map((e: any) => ({
        ...e,
        amount: typeof e?.amount === 'number' ? e.amount : parseFloat(String(e?.amount)) || 0,
        date: e?.date ? new Date(e.date).toISOString() : new Date().toISOString(),
      }))
      set({ expenses: normalized, isLoading: false })
    } catch {
      set({ isLoading: false, error: 'Failed to fetch expenses' })
    }
  },

  getExpense: async (id) => {
    const expense = await expenseService.getOne(id)
    set({ currentExpense: expense })
    return expense
  },

  createExpense: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const expense = await expenseService.create(data)
      set((state) => ({ expenses: [expense, ...state.expenses], isLoading: false }))
      return expense
    } catch {
      set({ isLoading: false, error: 'Failed to create expense' })
      throw new Error('Failed to create expense')
    }
  },

  updateExpense: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await expenseService.update(id, data)
      set((state) => ({
        expenses: state.expenses.map((e) => (e.id === id ? updated : e)),
        isLoading: false,
      }))
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update expense' })
      throw new Error('Failed to update expense')
    }
  },

  deleteExpense: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await expenseService.delete(id)
      set((state) => ({
        expenses: state.expenses.filter((e) => e.id !== id),
        isLoading: false,
      }))
    } catch {
      set({ isLoading: false, error: 'Failed to delete expense' })
    }
  },

  clearError: () => set({ error: null }),
}))

// ── Budget Store ───────────────────────────────────────────────────────

type BudgetAlert = { id?: number; message?: string; description?: string }

interface BudgetState {
  budgets: readonly Budget[]
  alerts: readonly BudgetAlert[]
  isLoading: boolean
  error: string | null
}

interface BudgetActions {
  fetchBudgets: (filters?: BudgetFilters) => Promise<void>
  fetchAlerts: () => Promise<void>
  createBudget: (data: BudgetCreateData) => Promise<Budget>
  updateBudget: (id: number, data: Partial<BudgetCreateData>) => Promise<Budget>
  deleteBudget: (id: number) => Promise<void>
  clearError: () => void
}

export const useBudgetStore = create<BudgetState & BudgetActions>((set) => ({
  budgets: [],
  alerts: [],
  isLoading: false,
  error: null,

  fetchBudgets: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await budgetService.getAll(filters)
      // Normalize budgets: ensure allocated_amount and recommended_amount and spent_amount are numbers
      const normalized = (data || []).map((b: any) => ({
        ...b,
        allocated_amount: typeof b?.allocated_amount === 'number' ? b.allocated_amount : parseFloat(String(b?.allocated_amount)) || 0,
        recommended_amount: b?.recommended_amount != null ? (parseFloat(String(b.recommended_amount)) || 0) : undefined,
        spent_amount: typeof b?.spent_amount === 'number' ? b.spent_amount : parseFloat(String(b?.spent_amount)) || 0,
        month: b?.month || null,
      }))
      set({ budgets: normalized, isLoading: false })
    } catch {
      set({ isLoading: false, error: 'Failed to fetch budgets' })
    }
  },

  fetchAlerts: async () => {
    try {
      const data = await budgetService.getAlerts()
      // budgetService.getAlerts may return different shapes; normalize to array if needed
      const alertsArray = Array.isArray(data) ? data : (data ? (Array.isArray((data as any).alerts) ? (data as any).alerts : [data]) : [])
      set({ alerts: alertsArray })
    } catch {
      set({ error: 'Failed to fetch alerts' })
    }
  },

  createBudget: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const budget = await budgetService.create(data)
      set((state) => ({ budgets: [budget, ...state.budgets], isLoading: false }))
      return budget
    } catch {
      set({ isLoading: false, error: 'Failed to create budget' })
      throw new Error('Failed to create budget')
    }
  },

  updateBudget: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await budgetService.update(id, data)
      set((state) => ({
        budgets: state.budgets.map((b) => (b.id === id ? updated : b)),
        isLoading: false,
      }))
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update budget' })
      throw new Error('Failed to update budget')
    }
  },

  deleteBudget: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await budgetService.delete(id)
      set((state) => ({ budgets: state.budgets.filter((b) => b.id !== id), isLoading: false }))
    } catch {
      set({ isLoading: false, error: 'Failed to delete budget' })
    }
  },

  clearError: () => set({ error: null }),
}))

// ── Goal Store ─────────────────────────────────────────────────────────

interface GoalState {
  goals: readonly Goal[]
  isLoading: boolean
  error: string | null
}

interface GoalActions {
  fetchGoals: (filters?: GoalFilters) => Promise<void>
  createGoal: (data: GoalCreateData) => Promise<Goal>
  updateGoal: (id: number, data: Partial<GoalCreateData>) => Promise<Goal>
  deleteGoal: (id: number) => Promise<void>
  addProgress: (id: number, amount: number) => Promise<Goal>
  clearError: () => void
}

export const useGoalStore = create<GoalState & GoalActions>((set) => ({
  goals: [],
  isLoading: false,
  error: null,

  fetchGoals: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await goalService.getAll(filters)
      set({ goals: data, isLoading: false })
    } catch {
      set({ isLoading: false, error: 'Failed to fetch goals' })
    }
  },

  createGoal: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const goal = await goalService.create(data)
      set((state) => ({ goals: [goal, ...state.goals], isLoading: false }))
      return goal
    } catch {
      set({ isLoading: false, error: 'Failed to create goal' })
      throw new Error('Failed to create goal')
    }
  },

  updateGoal: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await goalService.update(id, data)
      set((state) => ({
        goals: state.goals.map((g) => (g.id === id ? updated : g)),
        isLoading: false,
      }))
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update goal' })
      throw new Error('Failed to update goal')
    }
  },

  deleteGoal: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await goalService.delete(id)
      set((state) => ({
        goals: state.goals.filter((g) => g.id !== id),
        isLoading: false,
      }))
    } catch {
      set({ isLoading: false, error: 'Failed to delete goal' })
    }
  },

  addProgress: async (id, amount) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await goalService.addProgress(id, amount)
      set((state) => ({
        goals: state.goals.map((g) => (g.id === id ? updated : g)),
        isLoading: false,
      }))
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update progress' })
      throw new Error('Failed to update progress')
    }
  },

  clearError: () => set({ error: null }),
}))

// ── Loan Store ─────────────────────────────────────────────────────────

interface LoanState {
  loans: readonly Loan[]
  isLoading: boolean
  error: string | null
}

interface LoanActions {
  fetchLoans: (filters?: LoanFilters) => Promise<void>
  createLoan: (data: LoanCreateData) => Promise<Loan>
  updateLoan: (id: number, data: Partial<LoanCreateData>) => Promise<Loan>
  deleteLoan: (id: number) => Promise<void>
  clearError: () => void
}

export const useLoanStore = create<LoanState & LoanActions>((set) => ({
  loans: [],
  isLoading: false,
  error: null,

  fetchLoans: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await loanService.getAll(filters)
      // Normalize loans: numeric financial fields
      const normalized = (data || []).map((l: any) => ({
        ...l,
        principal_amount: typeof l?.principal_amount === 'number' ? l.principal_amount : parseFloat(String(l?.principal_amount || l?.amount)) || 0,
        amount: typeof l?.amount === 'number' ? l.amount : parseFloat(String(l?.amount)) || 0,
        emi_amount: typeof l?.emi_amount === 'number' ? l.emi_amount : parseFloat(String(l?.emi_amount)) || 0,
        outstanding_balance: typeof l?.outstanding_balance === 'number' ? l.outstanding_balance : parseFloat(String(l?.outstanding_balance)) || 0,
        interest_rate: typeof l?.interest_rate === 'number' ? l.interest_rate : parseFloat(String(l?.interest_rate)) || 0,
        loan_term_months: typeof l?.loan_term_months === 'number' ? l.loan_term_months : parseInt(String(l?.loan_term_months), 10) || 0,
        remaining_months: l?.remaining_months != null ? parseInt(String(l.remaining_months), 10) || 0 : undefined,
      }))
      set({ loans: normalized, isLoading: false })
    } catch {
      set({ isLoading: false, error: 'Failed to fetch loans' })
    }
  },

  createLoan: async (data) => {
    set({ isLoading: true, error: null })
    try {
      const loan = await loanService.create(data)
      set((state) => ({ loans: [loan, ...state.loans], isLoading: false }))
      return loan
    } catch {
      set({ isLoading: false, error: 'Failed to create loan' })
      throw new Error('Failed to create loan')
    }
  },

  updateLoan: async (id, data) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await loanService.update(id, data)
      set((state) => ({
        loans: state.loans.map((l) => (l.id === id ? updated : l)),
        isLoading: false,
      }))
      return updated
    } catch {
      set({ isLoading: false, error: 'Failed to update loan' })
      throw new Error('Failed to update loan')
    }
  },

  deleteLoan: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await loanService.delete(id)
      set((state) => ({
        loans: state.loans.filter((l) => l.id !== id),
        isLoading: false,
      }))
    } catch {
      set({ isLoading: false, error: 'Failed to delete loan' })
    }
  },

  clearError: () => set({ error: null }),
}))

// ── Notification Store ─────────────────────────────────────────────────

interface NotificationState {
  notifications: readonly Notification[]
  isLoading: boolean
  error: string | null
}

interface NotificationActions {
  fetchNotifications: () => Promise<void>
  markNotificationAsRead: (id: number) => Promise<void>
  deleteNotification: (id: number) => Promise<void>
  addNotification: (notification: Notification) => void
  clearError: () => void
}

export const useNotificationStore = create<NotificationState & NotificationActions>((set) => ({
  notifications: [],
  isLoading: false,
  error: null,

  fetchNotifications: async () => {
    set({ isLoading: true, error: null })
    try {
      const data = await notificationService.getAll()
      set({ notifications: data, isLoading: false })
    } catch {
      set({ isLoading: false, error: 'Failed to fetch notifications' })
    }
  },

  markNotificationAsRead: async (id) => {
    try {
      await notificationService.markAsRead(id)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n,
        ),
      }))
    } catch {
      // Non-critical — silently fail
    }
  },

  deleteNotification: async (id) => {
    try {
      await notificationService.delete(id)
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }))
    } catch {
      // Non-critical
    }
  },

  addNotification: (notification) => {
    set((state) => ({
      notifications: [notification, ...state.notifications],
    }))
  },

  clearError: () => set({ error: null }),
}))
