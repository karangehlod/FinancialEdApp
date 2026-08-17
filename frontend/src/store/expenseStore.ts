import { create } from 'zustand'
import { expenseService } from '@/services/apiService'
import type { Expense, ExpenseCreateData, ExpenseFilters } from '@/types'

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
