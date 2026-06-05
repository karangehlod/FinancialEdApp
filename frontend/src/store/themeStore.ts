/**
 * Theme store — persisted dark/light/system preference.
 */

import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Theme } from '@/types'

interface ThemeState {
  theme: Theme
}

interface ThemeActions {
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  initTheme: () => void
}

type ThemeStore = ThemeState & ThemeActions

function applyTheme(theme: Theme): void {
  const root = document.documentElement
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  if (theme === 'dark' || (theme === 'system' && prefersDark)) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }
}

export const useThemeStore = create<ThemeStore>()(
  persist(
    (set, get) => ({
      theme: 'light',

      setTheme: (theme) => {
        set({ theme })
        applyTheme(theme)
      },

      toggleTheme: () => {
        const next: Theme = get().theme === 'dark' ? 'light' : 'dark'
        set({ theme: next })
        applyTheme(next)
      },

      initTheme: () => {
        applyTheme(get().theme)
      },
    }),
    { name: 'finedu-theme' },
  ),
)
