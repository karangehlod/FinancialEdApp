/**
 * Error Notification System - Toast-based error handling
 * 
 * Features:
 * - Toast notifications for API errors
 * - Categorized error types
 * - Auto-dismiss with configurable timeout
 * - User-friendly error messages
 * - Retry buttons for recoverable errors
 */

import { AlertCircle, AlertTriangle, Info, CheckCircle } from 'lucide-react'

export type ErrorSeverity = 'error' | 'warning' | 'info' | 'success'

export interface ErrorNotification {
  id: string
  title: string
  message: string
  severity: ErrorSeverity
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
  dismissible?: boolean
}

export interface ErrorContext {
  code: string
  statusCode?: number
  originalError?: unknown
  context?: Record<string, unknown>
}

/**
 * Error message formatter for user-friendly display
 */
export class ErrorMessageFormatter {
  /**
   * Get user-friendly error message
   */
  static formatError(error: unknown, context?: ErrorContext): { title: string; message: string } {
    if (error instanceof Error) {
      return this.formatErrorInstance(error)
    }

    if (typeof error === 'object' && error !== null) {
      return this.formatErrorObject(error as Record<string, unknown>, context)
    }

    return {
      title: 'An error occurred',
      message: 'Something went wrong. Please try again.',
    }
  }

  private static formatErrorInstance(error: Error): { title: string; message: string } {
    // Handle specific error types
    if (error.name === 'AbortError') {
      return {
        title: 'Request Cancelled',
        message: 'Your request was cancelled. Please try again.',
      }
    }

    if (error.message.includes('Failed to fetch')) {
      return {
        title: 'Network Error',
        message: 'Unable to reach the server. Check your connection and try again.',
      }
    }

    if (error.message.includes('timeout')) {
      return {
        title: 'Request Timeout',
        message: 'The request took too long. Please try again.',
      }
    }

    // Generic error message
    return {
      title: 'Error',
      message: error.message || 'An unexpected error occurred.',
    }
  }

  private static formatErrorObject(obj: Record<string, unknown>, context?: ErrorContext): { title: string; message: string } {
    // Handle API error response format
    if ('response' in obj && typeof obj.response === 'object' && obj.response !== null) {
      const response = obj.response as Record<string, unknown>
      if ('data' in response) {
        const data = response.data as Record<string, unknown>
        if ('detail' in data || 'message' in data) {
          const message = (data.detail || data.message) as string
          return {
            title: this.getTitleForStatusCode(context?.statusCode),
            message,
          }
        }
      }
    }

    // Handle structured error response
    if ('detail' in obj || 'message' in obj || 'error' in obj) {
      const message = String(obj.detail || obj.message || obj.error)
      return {
        title: this.getTitleForStatusCode(context?.statusCode),
        message,
      }
    }

    return {
      title: 'Error',
      message: 'An unexpected error occurred.',
    }
  }

  private static getTitleForStatusCode(statusCode?: number): string {
    switch (statusCode) {
      case 400:
        return 'Invalid Request'
      case 401:
        return 'Unauthorized'
      case 403:
        return 'Forbidden'
      case 404:
        return 'Not Found'
      case 429:
        return 'Too Many Requests'
      case 500:
      case 502:
      case 503:
      case 504:
        return 'Server Error'
      default:
        return 'Error'
    }
  }
}

/**
 * Notification Manager - Manages toast notifications
 */
export class NotificationManager {
  private notifications: Map<string, ErrorNotification> = new Map()
  private listeners: Set<(notifications: ErrorNotification[]) => void> = new Set()
  private notificationIdCounter = 0

  /**
   * Show error notification
   */
  showError(error: unknown, context?: ErrorContext, action?: ErrorNotification['action']): string {
    const { title, message } = ErrorMessageFormatter.formatError(error, context)
    return this.show({
      title,
      message,
      severity: 'error',
      duration: 8000,
      action,
      dismissible: true,
    })
  }

  /**
   * Show warning notification
   */
  showWarning(title: string, message: string, action?: ErrorNotification['action']): string {
    return this.show({
      title,
      message,
      severity: 'warning',
      duration: 6000,
      action,
      dismissible: true,
    })
  }

  /**
   * Show info notification
   */
  showInfo(title: string, message: string): string {
    return this.show({
      title,
      message,
      severity: 'info',
      duration: 4000,
      dismissible: true,
    })
  }

  /**
   * Show success notification
   */
  showSuccess(title: string, message: string): string {
    return this.show({
      title,
      message,
      severity: 'success',
      duration: 3000,
      dismissible: true,
    })
  }

  /**
   * Show custom notification
   */
  show(notification: Omit<ErrorNotification, 'id'>): string {
    const id = this.generateId()
    const fullNotification: ErrorNotification = {
      ...notification,
      id,
    }

    this.notifications.set(id, fullNotification)
    this.notifyListeners()

    // Auto-dismiss if duration is set
    if (notification.duration && notification.duration > 0) {
      setTimeout(() => this.dismiss(id), notification.duration)
    }

    return id
  }

  /**
   * Dismiss a notification
   */
  dismiss(id: string): void {
    this.notifications.delete(id)
    this.notifyListeners()
  }

  /**
   * Dismiss all notifications
   */
  dismissAll(): void {
    this.notifications.clear()
    this.notifyListeners()
  }

  /**
   * Get all notifications
   */
  getNotifications(): ErrorNotification[] {
    return Array.from(this.notifications.values())
  }

  /**
   * Subscribe to notification changes
   */
  subscribe(listener: (notifications: ErrorNotification[]) => void): () => void {
    this.listeners.add(listener)
    // Call immediately with current notifications
    listener(this.getNotifications())
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener)
    }
  }

  // ── Private Methods ────────────────────────────────────

  private notifyListeners(): void {
    const notifications = this.getNotifications()
    this.listeners.forEach((listener) => listener(notifications))
  }

  private generateId(): string {
    return `notification_${++this.notificationIdCounter}`
  }
}

// Export singleton instance
export const notificationManager = new NotificationManager()

// Export icon mapping
export const getNotificationIcon = (severity: ErrorSeverity) => {
  switch (severity) {
    case 'error':
      return AlertCircle
    case 'warning':
      return AlertTriangle
    case 'info':
      return Info
    case 'success':
      return CheckCircle
  }
}

export const getNotificationStyles = (severity: ErrorSeverity) => {
  switch (severity) {
    case 'error':
      return 'bg-red-50 border-red-200 text-red-900'
    case 'warning':
      return 'bg-yellow-50 border-yellow-200 text-yellow-900'
    case 'info':
      return 'bg-blue-50 border-blue-200 text-blue-900'
    case 'success':
      return 'bg-green-50 border-green-200 text-green-900'
  }
}
