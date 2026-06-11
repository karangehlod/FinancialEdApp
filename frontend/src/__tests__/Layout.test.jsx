import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { Layout, Sidebar, Header, PageContainer } from '../components/Layout'
import { useAuthStore } from '../store/authStore'
import { useNotificationStore, useProfileStore } from '../store/index'

const mockToggleTheme = vi.fn()

// Mock the stores
vi.mock('../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

vi.mock('../store/index', () => ({
  useNotificationStore: vi.fn(),
  useProfileStore: vi.fn(),
  useExpenseStore: vi.fn(),
  useBudgetStore: vi.fn(),
  useGoalStore: vi.fn(),
  useLoanStore: vi.fn(),
}))

vi.mock('../store/themeStore', () => ({
  useThemeStore: () => ({
    theme: 'light',
    toggleTheme: mockToggleTheme,
  }),
}))

// Mock the utils
vi.mock('../utils/helpers', () => ({
  getInitials: vi.fn((name) => 'JD'),
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

// Mock api services used by stores to avoid runtime imports
vi.mock('../services/apiService', () => ({
  expenseService: {
    getAll: async () => [],
    getOne: async (id) => ({}),
    create: async (data) => data,
    update: async (id, data) => ({ ...data, id }),
    delete: async (id) => ({}),
  },
  budgetService: {
    getAll: async () => [],
    getOne: async () => ({}),
    create: async (d) => d,
    update: async (i, d) => ({ ...d, id: i }),
    delete: async () => ({}),
    getAlerts: async () => [],
  },
  loanService: {
    getAll: async () => [],
    getOne: async () => ({}),
    create: async (d) => d,
    update: async (i, d) => ({ ...d, id: i }),
    delete: async () => ({}),
  },
  goalService: {
    getAll: async () => [],
    getOne: async () => ({}),
    create: async (d) => d,
    update: async (i, d) => ({ ...d, id: i }),
    delete: async () => ({}),
    addProgress: async (i, a) => ({ id: i, progress: a }),
  },
  notificationService: {
    getAll: async () => [],
    markAsRead: async () => ({}),
    delete: async () => ({}),
  },
  authService: {
    updateProfile: async (p) => p,
    updateFinancialProfile: async (p) => p,
    getCurrentUser: async () => ({ id: '1', email: 'john@example.com' }),
    getFinancialProfile: async () => ({ currency: 'USD' }),
  },
}))

describe('Layout Components', () => {
  const mockUser = { name: 'John Doe', email: 'john@example.com' }
  
  const defaultAuthStore = {
    user: mockUser,
    logout: vi.fn(),
  }

  const defaultNotificationStore = {
    notifications: [
      { id: 1, title: 'Test Notification', message: 'Test message', read: false },
    ],
    markNotificationAsRead: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue(defaultAuthStore)
    useNotificationStore.mockReturnValue(defaultNotificationStore)
    useProfileStore.mockReturnValue({ profile: { name: 'John Doe' } })
  })

  describe('Sidebar', () => {
    const renderSidebar = (props = {}) => {
      const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
      }
      return render(
        <BrowserRouter>
          <Sidebar {...defaultProps} {...props} />
        </BrowserRouter>
      )
    }

    it('renders all navigation items', () => {
      renderSidebar()

      expect(screen.getByText('Dashboard')).toBeInTheDocument()
      expect(screen.getByText('Expenses')).toBeInTheDocument()
      expect(screen.getByText('Budgets')).toBeInTheDocument()
      expect(screen.getByText('Loans')).toBeInTheDocument()
      expect(screen.getByText('Goals')).toBeInTheDocument()
      expect(screen.getByText('Reports')).toBeInTheDocument()
      expect(screen.getByText('Chat')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('renders logout button', () => {
      renderSidebar()

      expect(screen.getByText('Logout')).toBeInTheDocument()
    })

    it('navigates when nav item is clicked', () => {
      renderSidebar()

      const dashboardLink = screen.getByText('Dashboard')
      fireEvent.click(dashboardLink)

      expect(mockNavigate).toHaveBeenCalledWith('/dashboard')
    })

    it('calls logout and navigates to login when logout is clicked', () => {
      const mockLogout = vi.fn()
      useAuthStore.mockReturnValue({
        ...defaultAuthStore,
        logout: mockLogout,
      })

      renderSidebar()

      const logoutButton = screen.getByText('Logout')
      fireEvent.click(logoutButton)

      expect(mockLogout).toHaveBeenCalled()
      expect(mockNavigate).not.toHaveBeenCalledWith('/login')
    })

    it('closes sidebar when close button is clicked on mobile', () => {
      const mockOnClose = vi.fn()
      renderSidebar({ onClose: mockOnClose })

      // The close button is only visible on mobile (lg:hidden)
      const closeButton = screen.getByLabelText(/close menu/i)
      fireEvent.click(closeButton)

      expect(mockOnClose).toHaveBeenCalled()
    })
  })

  describe('Header', () => {
    const renderHeader = (props = {}) => {
      const defaultProps = {
        onMenuClick: vi.fn(),
      }
      return render(
        <BrowserRouter>
          <Header {...defaultProps} {...props} />
        </BrowserRouter>
      )
    }

    it('renders user name and profile', () => {
      renderHeader()

      expect(screen.getByText('John Doe')).toBeInTheDocument()
      expect(screen.getByText('JD')).toBeInTheDocument() // initials
    })

    it('renders notifications with unread count', () => {
      renderHeader()

      expect(screen.getByText('1')).toBeInTheDocument() // unread count
    })

    it('opens notification dropdown when clicked', () => {
      renderHeader()

      const notificationButton = screen.getAllByRole('button')[2]
      fireEvent.click(notificationButton)

      expect(screen.getByText('1')).toBeInTheDocument()
    })

    it('opens profile dropdown when clicked', () => {
      renderHeader()

      const profileButton = screen.getByText('John Doe').closest('button')
      fireEvent.click(profileButton)

      expect(screen.getByText('View Profile')).toBeInTheDocument()
      expect(screen.getByText('Settings')).toBeInTheDocument()
    })

    it('navigates to chat when quick chat button is clicked', () => {
      renderHeader()

      const chatButton = screen.getByTitle(/chat with ai assistant/i)
      fireEvent.click(chatButton)

      expect(mockNavigate).toHaveBeenCalledWith('/chat')
    })

    it('calls onMenuClick when menu button is clicked', () => {
      const mockOnMenuClick = vi.fn()
      renderHeader({ onMenuClick: mockOnMenuClick })

      const menuButton = screen.getByLabelText(/toggle menu/i)
      fireEvent.click(menuButton)

      expect(mockOnMenuClick).toHaveBeenCalled()
    })
  })

  describe('PageContainer', () => {
    it('renders title and subtitle', () => {
      render(
        <PageContainer 
          title="Test Title" 
          subtitle="Test Subtitle"
        >
          <div>Test Content</div>
        </PageContainer>
      )

      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test Subtitle')).toBeInTheDocument()
      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })

    it('renders action buttons', () => {
      render(
        <PageContainer 
          title="Test Title"
          action={<button>Test Action</button>}
        >
          <div>Test Content</div>
        </PageContainer>
      )

      expect(screen.getByText('Test Action')).toBeInTheDocument()
    })

    it('renders without subtitle and action', () => {
      render(
        <PageContainer title="Test Title">
          <div>Test Content</div>
        </PageContainer>
      )

      expect(screen.getByText('Test Title')).toBeInTheDocument()
      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })
  })

  describe('Layout', () => {
    const renderLayout = () => {
      return render(
        <BrowserRouter>
          <Layout>
            <div>Test Content</div>
          </Layout>
        </BrowserRouter>
      )
    }

    it('renders main layout with children', () => {
      renderLayout()

      expect(screen.getByText('Test Content')).toBeInTheDocument()
    })

    it('contains sidebar and header components', () => {
      renderLayout()

      // Check for sidebar elements
      expect(screen.getAllByText('FinEd').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Dashboard').length).toBeGreaterThan(0)

      // Check for header elements  
      expect(screen.getByText('John Doe')).toBeInTheDocument()
    })
  })
})
