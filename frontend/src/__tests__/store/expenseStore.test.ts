/**
 * expenseStore — unit tests.
 * Verifies fetch, create, update, delete, and error paths.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useExpenseStore } from '@/store/expenseStore'

vi.mock('@/services/apiService', () => ({
  expenseService: {
    getAll: vi.fn(),
    getOne: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}))

import { expenseService } from '@/services/apiService'
const mock = expenseService as unknown as Record<string, ReturnType<typeof vi.fn>>

const EXPENSE = {
  id: 1,
  user_id: 'u1',
  amount: 25.5,
  description: 'Coffee',
  category: 'food' as const,
  date: '2025-06-01',
  created_at: '2025-06-01T10:00:00Z',
  updated_at: '2025-06-01T10:00:00Z',
}

const reset = () =>
  useExpenseStore.setState({ expenses: [], isLoading: false, error: null, currentExpense: null })

describe('expenseStore', () => {
  beforeEach(() => { reset(); vi.clearAllMocks() })

  describe('fetchExpenses', () => {
    it('populates expenses on success', async () => {
      mock.getAll.mockResolvedValueOnce([EXPENSE])
      await useExpenseStore.getState().fetchExpenses()
      expect(useExpenseStore.getState().expenses).toHaveLength(1)
      expect(useExpenseStore.getState().isLoading).toBe(false)
    })

    it('normalises amount to number', async () => {
      mock.getAll.mockResolvedValueOnce([{ ...EXPENSE, amount: '12.50' }])
      await useExpenseStore.getState().fetchExpenses()
      expect(useExpenseStore.getState().expenses[0]?.amount).toBe(12.5)
    })

    it('sets error on failure', async () => {
      mock.getAll.mockRejectedValueOnce(new Error('Network error'))
      await useExpenseStore.getState().fetchExpenses()
      expect(useExpenseStore.getState().error).toBeTruthy()
      expect(useExpenseStore.getState().isLoading).toBe(false)
    })
  })

  describe('createExpense', () => {
    it('prepends new expense to list', async () => {
      useExpenseStore.setState({ expenses: [EXPENSE] })
      const newExpense = { ...EXPENSE, id: 2, description: 'Lunch' }
      mock.create.mockResolvedValueOnce(newExpense)

      await useExpenseStore.getState().createExpense({
        amount: 15, description: 'Lunch', category: 'food', date: '2025-06-02',
      })

      const { expenses } = useExpenseStore.getState()
      expect(expenses[0]?.id).toBe(2)
      expect(expenses).toHaveLength(2)
    })

    it('throws and sets error on failure', async () => {
      mock.create.mockRejectedValueOnce(new Error('Server error'))
      await expect(
        useExpenseStore.getState().createExpense({ amount: 10, description: 'x', category: 'other', date: '2025-01-01' }),
      ).rejects.toThrow()
      expect(useExpenseStore.getState().error).toBeTruthy()
    })
  })

  describe('updateExpense', () => {
    it('replaces the updated expense in-place', async () => {
      useExpenseStore.setState({ expenses: [EXPENSE] })
      const updated = { ...EXPENSE, description: 'Espresso' }
      mock.update.mockResolvedValueOnce(updated)

      await useExpenseStore.getState().updateExpense(1, { description: 'Espresso' })

      expect(useExpenseStore.getState().expenses[0]?.description).toBe('Espresso')
    })
  })

  describe('deleteExpense', () => {
    it('removes expense from list', async () => {
      useExpenseStore.setState({ expenses: [EXPENSE] })
      mock.delete.mockResolvedValueOnce(undefined)

      await useExpenseStore.getState().deleteExpense(1)

      expect(useExpenseStore.getState().expenses).toHaveLength(0)
    })
  })

  describe('clearError', () => {
    it('resets error to null', () => {
      useExpenseStore.setState({ error: 'oops' })
      useExpenseStore.getState().clearError()
      expect(useExpenseStore.getState().error).toBeNull()
    })
  })
})
