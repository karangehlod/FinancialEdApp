/**
 * Shared test utilities following the testing-library best practices.
 * Provides typed render helpers, mock factories, and accessibility checkers.
 */
import { type ReactElement } from 'react'
import { render, type RenderResult } from '@testing-library/react'
import { BrowserRouter, MemoryRouter, type MemoryRouterProps } from 'react-router-dom'
import { vi } from 'vitest'
import type { User, Expense, Budget, Goal, Loan } from '../types'

// ── Render Helpers ─────────────────────────────────────────────────────────

export function renderWithRouter(
  ui: ReactElement,
  routerProps?: MemoryRouterProps,
): RenderResult {
  return render(
    <MemoryRouter {...routerProps}>
      {ui}
    </MemoryRouter>
  )
}

export function renderWithBrowserRouter(ui: ReactElement): RenderResult {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

// ── Mock Factories ─────────────────────────────────────────────────────────

export function makeUser(overrides: Partial<User> = {}): User {
  return {
    id: 1,
    email: 'test@example.com',
    name: 'Test User',
    first_name: 'Test',
    last_name: 'User',
    is_active: true,
    is_verified: true,
    two_factor_enabled: false,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    currency: 'USD',
    ...overrides,
  }
}

export function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 1,
    user_id: 1,
    amount: 25.50,
    description: 'Coffee',
    category: 'food',
    date: '2025-01-15',
    created_at: '2025-01-15T10:00:00Z',
    updated_at: '2025-01-15T10:00:00Z',
    ...overrides,
  }
}

export function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: 1,
    user_id: 1,
    category: 'food',
    amount: 500,
    spent: 100,
    month: 1,
    year: 2025,
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeGoal(overrides: Partial<Goal> = {}): Goal {
  return {
    id: 1,
    user_id: 1,
    title: 'Emergency Fund',
    description: null,
    target_amount: 10000,
    current_amount: 2500,
    deadline: '2026-01-01',
    status: 'active',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    ...overrides,
  }
}

export function makeLoan(overrides: Partial<Loan> = {}): Loan {
  return {
    id: 1,
    user_id: 1,
    name: 'Car Loan',
    principal: 20000,
    interest_rate: 5.5,
    term_months: 60,
    start_date: '2024-01-01',
    monthly_payment: 383.13,
    remaining_balance: 18000,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    ...overrides,
  }
}

// ── Auth Store Mock Factory ────────────────────────────────────────────────

export function makeAuthStoreMock(overrides = {}) {
  return {
    user: makeUser(),
    isAuthenticated: true,
    isLoading: false,
    error: null,
    tokenTimeRemaining: null,
    sessionWarning: false,
    login: vi.fn().mockResolvedValue({ access_token: 'token', refresh_token: 'refresh' }),
    register: vi.fn().mockResolvedValue(makeUser()),
    logout: vi.fn(),
    fetchCurrentUser: vi.fn().mockResolvedValue(makeUser()),
    clearError: vi.fn(),
    initAuth: vi.fn().mockResolvedValue(true),
    updateProfile: vi.fn().mockResolvedValue(makeUser()),
    updateTokenStatus: vi.fn(),
    showSessionWarning: vi.fn(),
    dismissSessionWarning: vi.fn(),
    refreshSession: vi.fn().mockResolvedValue(true),
    setUser: vi.fn(),
    ...overrides,
  }
}
