import { create } from 'zustand'
import { budgetService } from '@/services/apiService'
import type { Budget, BudgetCreateData, BudgetFilters } from '@/types'

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
      const alertsArray = Array.isArray(data)
        ? data
        : (data ? (Array.isArray((data as any).alerts) ? (data as any).alerts : [data]) : [])
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
