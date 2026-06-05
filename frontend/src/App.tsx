/**
 * App — root application component.
 *
 * Features:
 *   - Route-based code splitting via React.lazy
 *   - Global error boundary
 *   - Session warning modal
 *   - Protected routes with RBAC for admin
 *   - React Router v6 with future-flag opt-ins
 *   - Toast notifications
 *   - Theme initialization
 */

import { useEffect, Suspense, lazy } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useInitAuth } from '@/hooks/useAuth'
import { useThemeStore } from '@/store/themeStore'
import { ErrorBoundary } from '@/components/ErrorBoundary'
import { SessionWarning } from '@/components/SessionWarning'
import { ProtectedRoute } from '@/components/ProtectedRoute'
import { LoadingSpinner } from '@/components/UI'
import { ToastContainer } from '@/components/ToastContainer'

// ── Lazy-loaded pages (route-based code splitting) ─────────────────────

const LoginPage = lazy(() =>
  import('./pages/LoginPage').then((m) => ({ default: m.LoginPage })),
)
const RegisterPage = lazy(() =>
  import('./pages/RegisterPage').then((m) => ({ default: m.RegisterPage })),
)
const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((m) => ({ default: m.DashboardPage })),
)
const ExpensesPage = lazy(() =>
  import('./pages/ExpensesPage').then((m) => ({ default: m.ExpensesPage })),
)
const BudgetsPage = lazy(() =>
  import('./pages/BudgetsPage').then((m) => ({ default: m.BudgetsPage })),
)
const GoalsPage = lazy(() =>
  import('./pages/GoalsPage').then((m) => ({ default: m.GoalsPage })),
)
const LoansPage = lazy(() =>
  import('./pages/LoansPage').then((m) => ({ default: m.LoansPage })),
)
const ReportsPage = lazy(() =>
  import('./pages/ReportsPage').then((m) => ({ default: m.ReportsPage })),
)
const SettingsPage = lazy(() =>
  import('./pages/SettingsPage').then((m) => ({ default: m.SettingsPage })),
)
const ChatPage = lazy(() =>
  import('./pages/ChatPage').then((m) => ({ default: m.ChatPage })),
)
const AdminPage = lazy(() =>
  import('./pages/AdminPage').then((m) => ({ default: m.AdminPage })),
)
const OAuthCallbackPage = lazy(() => import('./pages/OAuthCallbackPage'))

// ── Loading Fallback ───────────────────────────────────────────────────

function LoadingFallback(): JSX.Element {
  return (
    <div className="flex items-center justify-center min-h-[60vh] sm:min-h-screen" role="status">
      <LoadingSpinner size="md" />
    </div>
  )
}

// ── Router ──────────────────────────────────────────────────────────────

const router = createBrowserRouter([
  // Public routes
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  { path: '/auth/callback', element: <OAuthCallbackPage /> },

  // Protected routes
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <DashboardPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/expenses',
    element: (
      <ProtectedRoute>
        <ExpensesPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/budgets',
    element: (
      <ProtectedRoute>
        <BudgetsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/goals',
    element: (
      <ProtectedRoute>
        <GoalsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/loans',
    element: (
      <ProtectedRoute>
        <LoansPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/reports',
    element: (
      <ProtectedRoute>
        <ReportsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/settings',
    element: (
      <ProtectedRoute>
        <SettingsPage />
      </ProtectedRoute>
    ),
  },
  {
    path: '/chat',
    element: (
      <ProtectedRoute>
        <ChatPage />
      </ProtectedRoute>
    ),
  },
  // Admin route — restricted to admin role
  {
    path: '/admin',
    element: (
      <ProtectedRoute allowedRoles={['admin']}>
        <AdminPage />
      </ProtectedRoute>
    ),
  },

  // Catch-all redirects
  { path: '/', element: <Navigate to="/dashboard" replace /> },
  { path: '*', element: <Navigate to="/dashboard" replace /> },
])

// ── App Component ──────────────────────────────────────────────────────

export default function App(): JSX.Element {
  // Bootstrap auth on mount (runs once, before Router context)
  useInitAuth()

  // Initialize theme on mount
  const initTheme = useThemeStore((s) => s.initTheme)
  useEffect(() => {
    initTheme()
  }, [initTheme])

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingFallback />}>
        <SessionWarning />
        <ToastContainer />
        <RouterProvider router={router} />
      </Suspense>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4_000,
          style: {
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
          },
        }}
      />
    </ErrorBoundary>
  )
}
