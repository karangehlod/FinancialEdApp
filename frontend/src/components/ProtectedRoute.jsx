import React from 'react'
import { useAuthStore } from '../store/authStore'
import { LoadingSpinner } from '../components/UI'

/**
 * ProtectedRoute Component - Wraps routes that require authentication
 */
export const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary-600 to-secondary-600">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null // Navigation will handle the redirect
  }

  return children
}
