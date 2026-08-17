import { create } from 'zustand'
import { goalService } from '@/services/apiService'
import type { Goal, GoalCreateData, GoalFilters } from '@/types'

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
