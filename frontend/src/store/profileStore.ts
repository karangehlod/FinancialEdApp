import { create } from 'zustand'
import { authService } from '@/services/apiService'
import type { User, FinancialProfile } from '@/types'

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
