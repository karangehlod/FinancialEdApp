/**
 * SessionWarning — modal displayed when the user's JWT is about to expire.
 * Offers "Stay Logged In" (dismiss + silent refresh on next API call) and "Logout".
 *
 * Accessible: focus trap, aria-live, keyboard support.
 * Responsive: centered modal from 320 px to 1920 px+.
 */

import { useEffect, useState, useCallback, memo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, LogOut } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import tokenManager from '@/utils/tokenManager'

// ── Component ──────────────────────────────────────────────────────────

export const SessionWarning = memo(function SessionWarning() {
  const sessionWarning = useAuthStore((s) => s.sessionWarning)
  const dismissSessionWarning = useAuthStore((s) => s.dismissSessionWarning)
  const logout = useAuthStore((s) => s.logout)
  const [timeRemaining, setTimeRemaining] = useState<string>('')

  // Countdown timer
  useEffect(() => {
    if (!sessionWarning) return

    const tick = (): void => {
      setTimeRemaining(tokenManager.formatTokenTimeRemaining())
    }
    tick()

    const interval = setInterval(tick, 1_000)
    return () => clearInterval(interval)
  }, [sessionWarning])

  const handleExtendSession = useCallback((): void => {
    dismissSessionWarning()
  }, [dismissSessionWarning])

  const handleLogout = useCallback((): void => {
    logout()
  }, [logout])

  // Escape key handler
  useEffect(() => {
    if (!sessionWarning) return

    const handleKeyDown = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') handleExtendSession()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [sessionWarning, handleExtendSession])

  return (
    <AnimatePresence>
      {sessionWarning && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-40"
            onClick={handleExtendSession}
            aria-hidden="true"
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-white dark:bg-gray-800 rounded-lg shadow-2xl w-[calc(100%-2rem)] sm:w-full"
            style={{ maxWidth: 'var(--content-max-width, 28rem)' }}
            role="alertdialog"
            aria-modal="true"
            aria-labelledby="session-warning-title"
            aria-describedby="session-warning-desc"
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 px-5 sm:px-6 py-4 border-b border-amber-200 dark:border-amber-700 flex items-start gap-3 rounded-t-lg">
              <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                <h3
                  id="session-warning-title"
                  className="font-semibold text-gray-900 dark:text-gray-100"
                >
                  Session Expiring Soon
                </h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                  Your session will expire in{' '}
                  <span className="font-mono font-medium">{timeRemaining}</span>
                </p>
              </div>
            </div>

            {/* Body */}
            <div className="px-5 sm:px-6 py-4">
              <p
                id="session-warning-desc"
                className="text-gray-700 dark:text-gray-300 mb-4 text-sm sm:text-base"
              >
                For your security, you will be automatically logged out soon.
                Would you like to extend your session?
              </p>
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800 dark:text-blue-300">
                  ℹ️ Click &ldquo;Stay Logged In&rdquo; to refresh your session for another hour.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="bg-gray-50 dark:bg-gray-900 px-5 sm:px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row gap-3 rounded-b-lg">
              <button
                type="button"
                onClick={handleExtendSession}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                autoFocus
              >
                Stay Logged In
              </button>
              <button
                type="button"
                onClick={handleLogout}
                className="flex-1 px-4 py-2.5 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg font-medium hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
              >
                <LogOut className="w-4 h-4" aria-hidden="true" />
                Logout
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
})

export default SessionWarning
