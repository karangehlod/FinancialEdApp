import React, { useEffect, useState } from 'react'
import { useAuthStore } from '../store/authStore'
import tokenManager from '../utils/tokenManager'
import { AlertCircle, LogOut } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

/**
 * Session Warning Modal - Shows when token is about to expire
 */
export const SessionWarning = () => {
  const { sessionWarning, dismissSessionWarning, logout } = useAuthStore()
  const [timeRemaining, setTimeRemaining] = useState('')

  useEffect(() => {
    if (!sessionWarning) return

    const interval = setInterval(() => {
      setTimeRemaining(tokenManager.formatTokenTimeRemaining())
    }, 1000)

    return () => clearInterval(interval)
  }, [sessionWarning])

  const handleExtendSession = () => {
    dismissSessionWarning()
    // Token will be refreshed on next API call
  }

  const handleLogout = () => {
    // authStore.logout performs token cleanup and will redirect to /login
    logout()
  }

  return (
    <AnimatePresence>
      {sessionWarning && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={handleExtendSession}
          />

          {/* Modal */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: -20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: -20 }}
            transition={{ type: 'spring', damping: 20, stiffness: 300 }}
            className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 z-50 bg-white rounded-lg shadow-2xl w-full mx-4"
            style={{ maxWidth: 'var(--content-max-width)' }}
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-amber-50 to-orange-50 px-6 py-4 border-b border-amber-200 flex items-start gap-3">
              <AlertCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-amber-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="font-semibold text-gray-900">Session Expiring Soon</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Your session will expire in {timeRemaining}
                </p>
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-4">
              <p className="text-gray-700 mb-4">
                For your security, you will be automatically logged out in 5 minutes. Would you like to extend your session?
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">
                  ℹ️ Click "Stay Logged In" to refresh your session for another hour.
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="bg-gray-50 px-6 py-4 border-t border-gray-200 flex gap-3">
              <button
                onClick={handleExtendSession}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
              >
                Stay Logged In
              </button>
              <button
                onClick={handleLogout}
                className="flex-1 px-4 py-2 bg-gray-200 text-gray-800 rounded-lg font-medium hover:bg-gray-300 transition-colors flex items-center justify-center gap-2"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default SessionWarning
