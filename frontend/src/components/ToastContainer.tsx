/**
 * Toast Notification Component - Displays error/success notifications
 * 
 * Features:
 * - Multiple notifications in a queue
 * - Auto-dismiss with progress bar
 * - Dismissible by user
 * - Action buttons for retries
 * - Fully accessible (ARIA)
 */

import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { notificationManager, getNotificationIcon, getNotificationStyles, type ErrorNotification } from '@/utils/errorNotificationManager'

/**
 * Individual Toast Component
 */
function Toast({ notification, onDismiss }: { notification: ErrorNotification; onDismiss: () => void }) {
  const [isExiting, setIsExiting] = useState(false)
  const Icon = getNotificationIcon(notification.severity)
  const styles = getNotificationStyles(notification.severity)

  const handleDismiss = () => {
    setIsExiting(true)
    setTimeout(onDismiss, 200)
  }

  useEffect(() => {
    if (notification.duration && notification.duration > 0) {
      const timer = setTimeout(handleDismiss, notification.duration)
      return () => clearTimeout(timer)
    }
  }, [notification.duration])

  return (
    <div
      className={`
        transform transition-all duration-200 ease-out
        ${isExiting ? 'opacity-0 translate-x-full' : 'opacity-100 translate-x-0'}
      `}
      role="alert"
      aria-live="polite"
    >
      <div className={`border rounded-lg shadow-lg p-4 ${styles} flex items-start gap-3`}>
        <Icon className="w-5 h-5 flex-shrink-0 mt-0.5" />

        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm">{notification.title}</h3>
          <p className="text-sm opacity-90 mt-1">{notification.message}</p>

          {notification.action && (
            <button
              onClick={() => {
                notification.action?.onClick()
                handleDismiss()
              }}
              className="mt-3 text-sm font-medium underline hover:opacity-75 transition-opacity"
            >
              {notification.action.label}
            </button>
          )}
        </div>

        {notification.dismissible !== false && (
          <button
            onClick={handleDismiss}
            className="flex-shrink-0 opacity-50 hover:opacity-75 transition-opacity"
            aria-label="Dismiss notification"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  )
}

/**
 * Toast Container Component - Manages all notifications
 */
export function ToastContainer() {
  const [notifications, setNotifications] = useState<ErrorNotification[]>([])

  useEffect(() => {
    // Subscribe to notification changes
    const unsubscribe = notificationManager.subscribe(setNotifications)
    return unsubscribe
  }, [])

  const handleDismiss = (id: string) => {
    notificationManager.dismiss(id)
  }

  if (notifications.length === 0) {
    return null
  }

  return (
    <div
      className="fixed top-4 right-4 z-50 space-y-3 max-w-md"
      role="region"
      aria-label="Notifications"
    >
      {notifications.map((notification) => (
        <Toast
          key={notification.id}
          notification={notification}
          onDismiss={() => handleDismiss(notification.id)}
        />
      ))}
    </div>
  )
}

export default ToastContainer
