import { create } from 'zustand'
import {
  expenseService,
  budgetService,
  loanService,
  goalService,
  notificationService,
  authService,
} from '../services/apiService.js'

// Profile Store - For user profile and financial profile
export const useProfileStore = create((set) => ({
  profile: null,
  financialProfile: null,
  isLoading: false,
  error: null,
  currency: 'USD',

  // Update user profile (currency, preferences, name, etc)
  updateProfile: async (profileData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await authService.updateProfile(profileData)
      set({
        profile: updated,
        currency: updated.currency || 'USD',
        isLoading: false,
      })
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update profile' })
      throw error
    }
  },

  // Update financial profile (salary, rent, insurance, etc)
  updateFinancialProfile: async (financialData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await authService.updateFinancialProfile(financialData)
      set({
        financialProfile: updated,
        currency: updated.currency || 'USD',
        isLoading: false,
      })
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update financial profile' })
      throw error
    }
  },

  // Fetch current user profile
  fetchProfile: async () => {
    set({ isLoading: true, error: null })
    try {
      const user = await authService.getCurrentUser()
      set({
        profile: user,
        isLoading: false,
      })
      return user
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch profile' })
    }
  },

  // Fetch financial profile
  fetchFinancialProfile: async () => {
    set({ isLoading: true, error: null })
    try {
      const financialProfile = await authService.getFinancialProfile()
      set({
        financialProfile: financialProfile,
        currency: financialProfile.currency || 'USD',
        isLoading: false,
      })
      return financialProfile
    } catch (error) {
      // 404 is expected for new users — not a real error
      if (error.response?.status === 404) {
        set({ isLoading: false, financialProfile: null })
      } else {
        set({ isLoading: false, error: 'Failed to fetch financial profile' })
        console.error('Error fetching financial profile:', error)
      }
    }
  },

  // Set currency (for UI use)
  setCurrency: (currency) => {
    set({ currency })
  },

  clearError: () => set({ error: null }),
}))

// Expenses Store
export const useExpenseStore = create((set) => ({
  expenses: [],
  isLoading: false,
  error: null,
  currentExpense: null,

  fetchExpenses: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await expenseService.getAll(filters)
      set({ expenses: data, isLoading: false })
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch expenses' })
    }
  },

  getExpense: async (id) => {
    try {
      const expense = await expenseService.getOne(id)
      set({ currentExpense: expense })
      return expense
    } catch (error) {
      set({ error: 'Failed to fetch expense' })
    }
  },

  addExpense: async (expenseData) => {
    set({ isLoading: true, error: null })
    try {
      const newExpense = await expenseService.create(expenseData)
      set((state) => ({
        expenses: [...state.expenses, newExpense],
        isLoading: false,
      }))
      return newExpense
    } catch (error) {
      set({ isLoading: false, error: 'Failed to create expense' })
      throw error
    }
  },

  updateExpense: async (id, expenseData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await expenseService.update(id, expenseData)
      set((state) => ({
        expenses: state.expenses.map((e) => (e.id === id ? updated : e)),
        currentExpense: updated,
        isLoading: false,
      }))
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update expense' })
      throw error
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
    } catch (error) {
      set({ isLoading: false, error: 'Failed to delete expense' })
      throw error
    }
  },

  clearError: () => set({ error: null }),
}))

// Budget Store
export const useBudgetStore = create((set) => ({
  budgets: [],
  alerts: [],
  isLoading: false,
  error: null,
  currentBudget: null,

  fetchBudgets: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await budgetService.getAll(filters)
      set({ budgets: data, isLoading: false })
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch budgets' })
    }
  },

  fetchAlerts: async () => {
    try {
      const data = await budgetService.getAlerts()
      set({ alerts: data })
    } catch (error) {
      set({ error: 'Failed to fetch alerts' })
    }
  },

  getBudget: async (id) => {
    try {
      const budget = await budgetService.getOne(id)
      set({ currentBudget: budget })
      return budget
    } catch (error) {
      set({ error: 'Failed to fetch budget' })
    }
  },

  addBudget: async (budgetData) => {
    set({ isLoading: true, error: null })
    try {
      const newBudget = await budgetService.create(budgetData)
      set((state) => ({
        budgets: [...state.budgets, newBudget],
        isLoading: false,
      }))
      return newBudget
    } catch (error) {
      set({ isLoading: false, error: 'Failed to create budget' })
      throw error
    }
  },

  updateBudget: async (id, budgetData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await budgetService.update(id, budgetData)
      set((state) => ({
        budgets: state.budgets.map((b) => (b.id === id ? updated : b)),
        currentBudget: updated,
        isLoading: false,
      }))
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update budget' })
      throw error
    }
  },

  deleteBudget: async (id) => {
    set({ isLoading: true, error: null })
    try {
      await budgetService.delete(id)
      set((state) => ({
        budgets: state.budgets.filter((b) => b.id !== id),
        isLoading: false,
      }))
    } catch (error) {
      set({ isLoading: false, error: 'Failed to delete budget' })
      throw error
    }
  },

  clearError: () => set({ error: null }),
}))

// Loan Store
export const useLoanStore = create((set) => ({
  loans: [],
  isLoading: false,
  error: null,
  currentLoan: null,

  fetchLoans: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await loanService.getAll(filters)
      set({ loans: data, isLoading: false })
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch loans' })
    }
  },

  getLoan: async (id) => {
    try {
      const loan = await loanService.getOne(id)
      set({ currentLoan: loan })
      return loan
    } catch (error) {
      set({ error: 'Failed to fetch loan' })
    }
  },

  addLoan: async (loanData) => {
    set({ isLoading: true, error: null })
    try {
      const newLoan = await loanService.create(loanData)
      set((state) => ({
        loans: [...state.loans, newLoan],
        isLoading: false,
      }))
      return newLoan
    } catch (error) {
      set({ isLoading: false, error: 'Failed to create loan' })
      throw error
    }
  },

  updateLoan: async (id, loanData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await loanService.update(id, loanData)
      set((state) => ({
        loans: state.loans.map((l) => (l.id === id ? updated : l)),
        currentLoan: updated,
        isLoading: false,
      }))
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update loan' })
      throw error
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
    } catch (error) {
      set({ isLoading: false, error: 'Failed to delete loan' })
      throw error
    }
  },

  clearError: () => set({ error: null }),
}))

// Goal Store
export const useGoalStore = create((set) => ({
  goals: [],
  isLoading: false,
  error: null,
  currentGoal: null,

  fetchGoals: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await goalService.getAll(filters)
      set({ goals: data, isLoading: false })
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch goals' })
    }
  },

  getGoal: async (id) => {
    try {
      const goal = await goalService.getOne(id)
      set({ currentGoal: goal })
      return goal
    } catch (error) {
      set({ error: 'Failed to fetch goal' })
    }
  },

  addGoal: async (goalData) => {
    set({ isLoading: true, error: null })
    try {
      const newGoal = await goalService.create(goalData)
      set((state) => ({
        goals: [...state.goals, newGoal],
        isLoading: false,
      }))
      return newGoal
    } catch (error) {
      set({ isLoading: false, error: 'Failed to create goal' })
      throw error
    }
  },

  updateGoal: async (id, goalData) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await goalService.update(id, goalData)
      set((state) => ({
        goals: state.goals.map((g) => (g.id === id ? updated : g)),
        currentGoal: updated,
        isLoading: false,
      }))
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to update goal' })
      throw error
    }
  },

  addProgress: async (id, amount) => {
    set({ isLoading: true, error: null })
    try {
      const updated = await goalService.addProgress(id, amount)
      set((state) => ({
        goals: state.goals.map((g) => (g.id === id ? updated : g)),
        currentGoal: updated,
        isLoading: false,
      }))
      return updated
    } catch (error) {
      set({ isLoading: false, error: 'Failed to add progress' })
      throw error
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
    } catch (error) {
      set({ isLoading: false, error: 'Failed to delete goal' })
      throw error
    }
  },

  clearError: () => set({ error: null }),
}))

// Notification Store
export const useNotificationStore = create((set) => ({
  notifications: [],
  isLoading: false,
  error: null,

  fetchNotifications: async (filters = {}) => {
    set({ isLoading: true, error: null })
    try {
      const data = await notificationService.getAll(filters)
      set({ notifications: data, isLoading: false })
    } catch (error) {
      set({ isLoading: false, error: 'Failed to fetch notifications' })
    }
  },

  markAsRead: async (id) => {
    try {
      await notificationService.markAsRead(id)
      set((state) => ({
        notifications: state.notifications.map((n) =>
          n.id === id ? { ...n, read: true } : n
        ),
      }))
    } catch (error) {
      set({ error: 'Failed to mark notification as read' })
    }
  },

  deleteNotification: async (id) => {
    try {
      await notificationService.delete(id)
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }))
    } catch (error) {
      set({ error: 'Failed to delete notification' })
    }
  },

  clearError: () => set({ error: null }),
}))
