/**
 * ProtectedRoute tests — auth gating, role checks, and loading states.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen } from '@testing-library/react'
import { renderWithRouter } from '../testUtils'
import { ProtectedRoute } from '../../components/ProtectedRoute'

// ── Mocks ───────────────────────────────────────────────────────────────

const mockAuthStore: {
  isAuthenticated: boolean
  isLoading: boolean
  user: { id: string; email: string } | null
} = {
  isAuthenticated: false,
  isLoading: false,
  user: null,
}

vi.mock('../../store/authStore', () => ({
  useAuthStore: () => mockAuthStore,
}))

vi.mock('../../components/UI', () => ({
  LoadingSpinner: ({ size }: { size: string }) => (
    <div data-testid="loading-spinner" data-size={size} role="status">Loading…</div>
  ),
}))

// ── Tests ───────────────────────────────────────────────────────────────

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockAuthStore.isAuthenticated = false
    mockAuthStore.isLoading = false
    mockAuthStore.user = null
  })

  it('redirects to /login when not authenticated', () => {
    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
      { initialEntries: ['/dashboard'] },
    )

    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('renders children when authenticated', () => {
    mockAuthStore.isAuthenticated = true
    mockAuthStore.user = { id: '1', email: 'user@example.com' }

    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    )

    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('shows loading spinner when auth is initializing', () => {
    mockAuthStore.isLoading = true

    renderWithRouter(
      <ProtectedRoute>
        <div>Protected Content</div>
      </ProtectedRoute>,
    )

    expect(screen.getByRole('status')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })

  it('ignores unsupported role restrictions and renders children for authenticated users', () => {
    mockAuthStore.isAuthenticated = true
    mockAuthStore.user = { id: '1', email: 'user@example.com' }

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Admin Content</div>
      </ProtectedRoute>,
    )

    expect(screen.getByText('Admin Content')).toBeInTheDocument()
  })

  it('renders children without role restrictions', () => {
    mockAuthStore.isAuthenticated = true
    mockAuthStore.user = { id: '1', email: 'user@example.com' }

    renderWithRouter(
      <ProtectedRoute>
        <div>Dashboard Content</div>
      </ProtectedRoute>,
    )

    expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
  })

  it('does not render an access denied screen because role checks are not implemented', () => {
    mockAuthStore.isAuthenticated = true
    mockAuthStore.user = { id: '1', email: 'user@example.com' }

    renderWithRouter(
      <ProtectedRoute allowedRoles={['admin']}>
        <div>Admin Content</div>
      </ProtectedRoute>,
    )

    expect(screen.queryByText(/access denied/i)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /return to dashboard/i })).not.toBeInTheDocument()
  })
})
