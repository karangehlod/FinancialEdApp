import { create } from 'zustand'
import { loanService } from '@/services/apiService'
import type { Loan, LoanCreateData, LoanFilters } from '@/types'

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
