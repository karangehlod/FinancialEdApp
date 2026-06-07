import React, { useEffect, Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useInitAuth, useProtectedRoute } from './hooks/useAuth'
import { useAuthStore } from './store/authStore'
import { useThemeStore } from './store/themeStore'
import ErrorBoundary from './components/ErrorBoundary'
import SessionWarning from './components/SessionWarning'
import tokenManager from './utils/tokenManager'

// Lazy load pages for code splitting
const LoginPage = lazy(() => import('./pages/LoginPage').then(m => ({ default: m.LoginPage })))
const RegisterPage = lazy(() => import('./pages/RegisterPage').then(m => ({ default: m.RegisterPage })))
const DashboardPage = lazy(() => import('./pages/DashboardPage').then(m => ({ default: m.DashboardPage })))
const ExpensesPage = lazy(() => import('./pages/ExpensesPage').then(m => ({ default: m.ExpensesPage })))
const BudgetsPage = lazy(() => import('./pages/BudgetsPage').then(m => ({ default: m.BudgetsPage })))
const GoalsPage = lazy(() => import('./pages/GoalsPage').then(m => ({ default: m.GoalsPage })))
const LoansPage = lazy(() => import('./pages/LoansPage').then(m => ({ default: m.LoansPage })))
const ReportsPage = lazy(() => import('./pages/ReportsPage').then(m => ({ default: m.ReportsPage })))
const SettingsPage = lazy(() => import('./pages/SettingsPage').then(m => ({ default: m.SettingsPage })))
const ChatPage = lazy(() => import('./pages/ChatPage').then(m => ({ default: m.ChatPage })))
const AdminPage = lazy(() => import('./pages/AdminPage').then(m => ({ default: m.AdminPage })))
const OAuthCallbackPage = lazy(() => import('./pages/OAuthCallbackPage'))

/**
 * Protected Route Wrapper
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore()

  if (isLoading) {
    return <LoadingFallback />
  }

  // If we have a valid token but auth store hasn't been populated yet,
  // avoid redirecting to /login immediately — show loading so auth can finish.
  const token = tokenManager.getAccessToken()
  if (!isAuthenticated && token && tokenManager.isTokenValid()) {
    return <LoadingFallback />
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />
}

/**
 * Loading fallback component
 */
const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-[60vh] sm:min-h-screen">
    <div style={{ width: 'var(--spinner-md)', height: 'var(--spinner-md)' }} className="animate-spin rounded-full border-b-2 border-primary-600" />
  </div>
)

/**
 * Main App Component
 */
export default function App() {
  useInitAuth()
  const initTheme = useThemeStore((s) => s.initTheme)
  useEffect(() => { initTheme() }, [initTheme])

  // Create router with v7 future flags to opt-in to upcoming behaviors and silence deprecation warnings
  const router = createBrowserRouter([
    { path: '/login', element: <LoginPage /> },
    { path: '/register', element: <RegisterPage /> },
    { path: '/auth/callback', element: <OAuthCallbackPage /> },

    { path: '/dashboard', element: <ProtectedRoute><DashboardPage /></ProtectedRoute> },
    { path: '/expenses', element: <ProtectedRoute><ExpensesPage /></ProtectedRoute> },
    { path: '/budgets', element: <ProtectedRoute><BudgetsPage /></ProtectedRoute> },
    { path: '/goals', element: <ProtectedRoute><GoalsPage /></ProtectedRoute> },
    { path: '/loans', element: <ProtectedRoute><LoansPage /></ProtectedRoute> },
    { path: '/reports', element: <ProtectedRoute><ReportsPage /></ProtectedRoute> },
    { path: '/settings', element: <ProtectedRoute><SettingsPage /></ProtectedRoute> },
    { path: '/chat', element: <ProtectedRoute><ChatPage /></ProtectedRoute> },
    { path: '/admin', element: <ProtectedRoute><AdminPage /></ProtectedRoute> },

    { path: '/', element: <Navigate to="/dashboard" replace /> },
    { path: '*', element: <Navigate to="/dashboard" replace /> },
  ], {
    future: {
      v7_startTransition: true,
      v7_relativeSplatPath: true,
    },
  })

  return (
    <ErrorBoundary>
      <>
        <Suspense fallback={<LoadingFallback />}>
          <SessionWarning />
          <RouterProvider router={router} />
        </Suspense>
        <Toaster position="top-right" />
       </>
     </ErrorBoundary>
   )
 }
