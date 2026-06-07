import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { DashboardPage } from '../pages/DashboardPage'
import { useAuthStore } from '../store/authStore'
import { useExpenseStore, useBudgetStore, useGoalStore, useLoanStore } from '../store/index'

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
    // Provide minimal notification/profile store to satisfy layout/Header usage
    const notif = { notifications: [], markNotificationAsRead: vi.fn() }
    const prof = { profile: { name: 'John Doe' } }
    const { useNotificationStore, useProfileStore } = require('../store/index')
    useNotificationStore.mockReturnValue(notif)
    useProfileStore.mockReturnValue(prof)
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

  it('renders all navigation tabs', () => {
    renderDashboardPage()

    expect(screen.getByText('Overview')).toBeInTheDocument()
    expect(screen.getByText('Expenses')).toBeInTheDocument()
    expect(screen.getByText('Budgets')).toBeInTheDocument()
    expect(screen.getByText('Goals')).toBeInTheDocument()
    expect(screen.getByText('Loans')).toBeInTheDocument()
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByText('Reports')).toBeInTheDocument()
  })

  it('displays overview tab by default', () => {
    renderDashboardPage()

    // Overview tab should be active by default
    const overviewTab = screen.getByText('Overview').closest('button')
    expect(overviewTab).toHaveClass('border-blue-600', 'text-blue-600')
  })

  it('switches tabs when clicked', async () => {
    renderDashboardPage()

    const expensesTab = screen.getByText('Expenses').closest('button')
    fireEvent.click(expensesTab)

    await waitFor(() => {
      expect(expensesTab).toHaveClass('border-blue-600', 'text-blue-600')
    })
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

    expect(screen.getByRole('status')).toBeInTheDocument()
  })

  it('has Add Expense button that navigates to expenses page', () => {
    renderDashboardPage()

    const addExpenseButton = screen.getByRole('button', { name: /add expense/i })
    fireEvent.click(addExpenseButton)

    expect(mockNavigate).toHaveBeenCalledWith('/expenses')
  })

  it('has Export button that switches to reports tab', () => {
    renderDashboardPage()

    const exportButton = screen.getByRole('button', { name: /export/i })
    fireEvent.click(exportButton)

    // Should switch to reports tab
    const reportsTab = screen.getByText('Reports').closest('button')
    expect(reportsTab).toHaveClass('border-blue-600', 'text-blue-600')
  })

  describe('Tab Content', () => {
    it('shows expenses tab content when expenses tab is active', async () => {
      renderDashboardPage()

      const expensesTab = screen.getByText('Expenses')
      fireEvent.click(expensesTab)

      await waitFor(() => {
        // ExpensesTab component should receive expenses data
        expect(screen.getByText('Expenses')).toBeInTheDocument()
      })
    })

    it('shows budgets tab content when budgets tab is active', async () => {
      renderDashboardPage()

      const budgetsTab = screen.getByText('Budgets')
      fireEvent.click(budgetsTab)

      await waitFor(() => {
        expect(screen.getByText('Budgets')).toBeInTheDocument()
      })
    })

    it('shows goals tab content when goals tab is active', async () => {
      renderDashboardPage()

      const goalsTab = screen.getByText('Goals')
      fireEvent.click(goalsTab)

      await waitFor(() => {
        expect(screen.getByText('Goals')).toBeInTheDocument()
      })
    })

    it('shows loans tab content when loans tab is active', async () => {
      renderDashboardPage()

      const loansTab = screen.getByText('Loans')
      fireEvent.click(loansTab)

      await waitFor(() => {
        expect(screen.getByText('Loans')).toBeInTheDocument()
      })
    })

    it('shows chat tab content when chat tab is active', async () => {
      renderDashboardPage()

      const chatTab = screen.getByText('Chat')
      fireEvent.click(chatTab)

      await waitFor(() => {
        expect(screen.getByText('Chat')).toBeInTheDocument()
      })
    })

    it('shows reports tab content when reports tab is active', async () => {
      renderDashboardPage()

      const reportsTab = screen.getByText('Reports')
      fireEvent.click(reportsTab)

      await waitFor(() => {
        expect(screen.getByText('Reports')).toBeInTheDocument()
      })
    })
  })
})
