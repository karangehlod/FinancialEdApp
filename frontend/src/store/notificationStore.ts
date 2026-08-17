import { create } from 'zustand'
import { notificationService } from '@/services/apiService'
import type { Notification } from '@/types'

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
