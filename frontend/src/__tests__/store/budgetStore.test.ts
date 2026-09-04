/**
 * budgetStore — unit tests.
 * Verifies fetch, create, update, delete, alert fetch, and error paths.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useBudgetStore } from '@/store/budgetStore'

vi.mock('@/services/apiService', () => ({
  budgetService: {
    getAll: vi.fn(),
    getAlerts: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
  },
}))

import { budgetService } from '@/services/apiService'
const mock = budgetService as unknown as Record<string, ReturnType<typeof vi.fn>>

const BUDGET = {
  id: 1,
  user_id: 'u1',
  category: 'food',
  amount: 500,
  spent: 120,
  allocated_amount: 500,
  spent_amount: 120,
  month: 6,
  year: 2025,
  created_at: '2025-06-01T00:00:00Z',
  updated_at: '2025-06-01T00:00:00Z',
}

const reset = () =>
  useBudgetStore.setState({ budgets: [], alerts: [], isLoading: false, error: null })

describe('budgetStore', () => {
  beforeEach(() => { reset(); vi.clearAllMocks() })

  describe('fetchBudgets', () => {
    it('populates budgets on success', async () => {
      mock.getAll.mockResolvedValueOnce([BUDGET])
      await useBudgetStore.getState().fetchBudgets()
      expect(useBudgetStore.getState().budgets).toHaveLength(1)
      expect(useBudgetStore.getState().isLoading).toBe(false)
    })

    it('normalises allocated_amount to number', async () => {
      mock.getAll.mockResolvedValueOnce([{ ...BUDGET, allocated_amount: '500.00' }])
      await useBudgetStore.getState().fetchBudgets()
      expect(useBudgetStore.getState().budgets[0]).toMatchObject({ allocated_amount: 500 })
    })

    it('sets error on failure', async () => {
      mock.getAll.mockRejectedValueOnce(new Error('Network'))
      await useBudgetStore.getState().fetchBudgets()
      expect(useBudgetStore.getState().error).toBeTruthy()
    })
  })

  describe('fetchAlerts', () => {
    it('stores alert array', async () => {
      mock.getAlerts.mockResolvedValueOnce([{ id: 1, message: 'Over budget!' }])
      await useBudgetStore.getState().fetchAlerts()
      expect(useBudgetStore.getState().alerts).toHaveLength(1)
    })

    it('handles wrapped alerts object', async () => {
      mock.getAlerts.mockResolvedValueOnce({ alerts: [{ id: 2 }] })
      await useBudgetStore.getState().fetchAlerts()
      expect(useBudgetStore.getState().alerts).toHaveLength(1)
    })
  })

  describe('createBudget', () => {
    it('prepends new budget', async () => {
      useBudgetStore.setState({ budgets: [BUDGET] })
      const newBudget = { ...BUDGET, id: 2, category: 'transport' }
      mock.create.mockResolvedValueOnce(newBudget)

      await useBudgetStore.getState().createBudget({ category: 'transport', amount: 200, month: 6, year: 2025 })

      const { budgets } = useBudgetStore.getState()
      expect(budgets[0]?.id).toBe(2)
      expect(budgets).toHaveLength(2)
    })

    it('throws on failure', async () => {
      mock.create.mockRejectedValueOnce(new Error('Server'))
      await expect(
        useBudgetStore.getState().createBudget({ category: 'food', amount: 100, month: 1, year: 2025 }),
      ).rejects.toThrow()
    })
  })

  describe('updateBudget', () => {
    it('replaces budget in-place', async () => {
      useBudgetStore.setState({ budgets: [BUDGET] })
      const updated = { ...BUDGET, amount: 600 }
      mock.update.mockResolvedValueOnce(updated)

      await useBudgetStore.getState().updateBudget(1, { amount: 600 })

      expect(useBudgetStore.getState().budgets[0]?.amount).toBe(600)
    })
  })

  describe('deleteBudget', () => {
    it('removes budget from list', async () => {
      useBudgetStore.setState({ budgets: [BUDGET] })
      mock.delete.mockResolvedValueOnce(undefined)

      await useBudgetStore.getState().deleteBudget(1)

      expect(useBudgetStore.getState().budgets).toHaveLength(0)
    })
  })

  describe('clearError', () => {
    it('resets error to null', () => {
      useBudgetStore.setState({ error: 'problem' })
      useBudgetStore.getState().clearError()
      expect(useBudgetStore.getState().error).toBeNull()
    })
  })
})
