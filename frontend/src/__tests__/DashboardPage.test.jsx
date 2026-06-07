import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { DashboardPage } from '../pages/DashboardPage'
import { useAuthStore } from '../store/authStore'
import {
  useExpenseStore,
  useBudgetStore,
  useGoalStore,
  useLoanStore,
  useNotificationStore,
  useProfileStore,
} from '../store/index'

// Mock all the stores
vi.mock('../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../store/index', () => ({
  useExpenseStore: vi.fn(),
  useBudgetStore: vi.fn(),
  useGoalStore: vi.fn(),
  useLoanStore: vi.fn(),
  useNotificationStore: vi.fn(),
  useProfileStore: vi.fn(),
}))

vi.mock('../store/themeStore', () => ({
  useThemeStore: () => ({
    theme: 'light',
    toggleTheme: vi.fn(),
  }),
}))

// Mock api services used by stores to avoid runtime imports
vi.mock('../services/apiService', () => ({
  expenseService: { getAll: async () => [] },
  budgetService: { getAll: async () => [] , getAlerts: async () => []},
  goalService: { getAll: async () => [] , addProgress: async () => ({})},
  loanService: { getAll: async () => [] },
  notificationService: { getAll: async () => [] },
  authService: { getCurrentUser: async () => ({ id: '1', email: 'john@example.com' }), getFinancialProfile: async () => ({ currency: 'USD' }) },
}))

// Mock the auth hook
vi.mock('../hooks/useAuth', () => ({
  useProtectedRoute: vi.fn(() => ({
    isAuthenticated: true,
    isLoading: false,
  })),
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ pathname: '/dashboard' }),
  }
})

describe('DashboardPage', () => {
  const mockUser = { name: 'John Doe', email: 'john@example.com' }
  
  const defaultAuthStore = {
    user: mockUser,
    isAuthenticated: true,
  }

  const defaultExpenseStore = {
    expenses: [
      { id: 1, amount: 50, category: 'Food', description: 'Lunch' },
      { id: 2, amount: 200, category: 'Transport', description: 'Uber' },
    ],
    fetchExpenses: vi.fn(),
    isLoading: false,
  }

  const defaultBudgetStore = {
    budgets: [
      { id: 1, category: 'Food', amount: 500, spent: 250 },
      { id: 2, category: 'Transport', amount: 300, spent: 200 },
    ],
    fetchBudgets: vi.fn(),
    isLoading: false,
  }

  const defaultGoalStore = {
    goals: [
      { id: 1, title: 'Emergency Fund', target: 10000, current: 5000 },
      { id: 2, title: 'Vacation', target: 3000, current: 1500 },
    ],
    fetchGoals: vi.fn(),
    isLoading: false,
  }

  const defaultLoanStore = {
    loans: [
      { id: 1, name: 'Car Loan', principal: 25000, balance: 15000 },
    ],
    fetchLoans: vi.fn(),
    isLoading: false,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue(defaultAuthStore)
    useExpenseStore.mockReturnValue(defaultExpenseStore)
    useBudgetStore.mockReturnValue(defaultBudgetStore)
    useGoalStore.mockReturnValue(defaultGoalStore)
    useLoanStore.mockReturnValue(defaultLoanStore)
    useNotificationStore.mockReturnValue({ notifications: [], markNotificationAsRead: vi.fn() })
    useProfileStore.mockReturnValue({ profile: { name: 'John Doe' } })
  })

  const renderDashboardPage = () => {
    return render(
      <BrowserRouter>
        <DashboardPage />
      </BrowserRouter>
    )
  }

  it('renders dashboard with user welcome message', () => {
    renderDashboardPage()

    expect(screen.getByText(/welcome back, john doe/i)).toBeInTheDocument()
    expect(screen.getByText(/manage your finances with detailed insights/i)).toBeInTheDocument()
  })

  it('renders dashboard actions and overview content', () => {
    renderDashboardPage()

    expect(screen.getByRole('button', { name: /add expense/i })).toBeInTheDocument()
    expect(screen.getByTitle(/view reports and export data/i)).toBeInTheDocument()
  })

  it('displays overview content by default', () => {
    renderDashboardPage()

    expect(screen.getByText(/welcome back, john doe/i)).toBeInTheDocument()
  })

  it('fetches all data on mount', () => {
    renderDashboardPage()

    expect(defaultExpenseStore.fetchExpenses).toHaveBeenCalled()
    expect(defaultBudgetStore.fetchBudgets).toHaveBeenCalled()
    expect(defaultGoalStore.fetchGoals).toHaveBeenCalled()
    expect(defaultLoanStore.fetchLoans).toHaveBeenCalled()
  })

  it('shows loading state when data is loading', () => {
    useExpenseStore.mockReturnValue({
      ...defaultExpenseStore,
      isLoading: true,
    })

    renderDashboardPage()

    expect(document.querySelector('.border-4.border-primary-200')).not.toBeNull()
  })

  it('has Add Expense button that navigates to expenses page', () => {
    renderDashboardPage()

    const addExpenseButton = screen.getByRole('button', { name: /add expense/i })
    fireEvent.click(addExpenseButton)

    expect(mockNavigate).toHaveBeenCalledWith('/expenses')
  })

  it('has Reports button that navigates to reports page', () => {
    renderDashboardPage()

    const exportButton = screen.getByTitle(/view reports and export data/i)
    fireEvent.click(exportButton)

    expect(mockNavigate).toHaveBeenCalledWith('/reports')
  })
})
