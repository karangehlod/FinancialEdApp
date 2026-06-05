/**
 * RegisterPage tests — form rendering, validation, password strength, and submission.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../testUtils'
import { RegisterPage } from '../../pages/RegisterPage'

// ── Mocks ───────────────────────────────────────────────────────────────

const mockRegister = vi.fn()
const mockClearError = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../store/authStore', () => ({
  useAuthStore: () => ({
    register: mockRegister,
    isLoading: false,
    error: null,
    clearError: mockClearError,
    isAuthenticated: false,
  }),
}))

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

vi.mock('../../utils/toast', () => ({
  showErrorToast: vi.fn(),
  showSuccessToast: vi.fn(),
}))

vi.mock('../../components/OAuthButtons', () => ({
  default: () => <div data-testid="oauth-buttons">OAuth</div>,
}))

vi.mock('../../components/Footer', () => ({
  Footer: () => <footer data-testid="footer">Footer</footer>,
}))

vi.mock('../../assets/FinEdLogo.png', () => ({ default: 'logo.png' }))

// ── Helpers ─────────────────────────────────────────────────────────────

const getNameField = () => document.getElementById('register-name') as HTMLInputElement
const getEmailField = () => document.getElementById('register-email') as HTMLInputElement
const getPasswordField = () => document.getElementById('register-password') as HTMLInputElement
const getConfirmField = () => document.getElementById('register-confirm') as HTMLInputElement

// ── Tests ───────────────────────────────────────────────────────────────

describe('RegisterPage', () => {
  const user = userEvent.setup()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the registration form with all required fields', () => {
    renderWithRouter(<RegisterPage />)

    expect(getNameField()).toBeInTheDocument()
    expect(getEmailField()).toBeInTheDocument()
    expect(getPasswordField()).toBeInTheDocument()
    expect(getConfirmField()).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('renders a link to the login page', () => {
    renderWithRouter(<RegisterPage />)

    const loginLink = screen.getAllByRole('link').find(
      (link) => link.getAttribute('href') === '/login',
    )
    expect(loginLink).toBeInTheDocument()
  })

  it('shows validation errors when submitting an empty form', async () => {
    renderWithRouter(<RegisterPage />)

    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/name is required/i)).toBeInTheDocument()
    })
  })

  it('shows email validation error for invalid email', async () => {
    renderWithRouter(<RegisterPage />)

    await user.type(getNameField(), 'Alice')
    await user.type(getEmailField(), 'not-an-email')
    await user.type(getPasswordField(), 'StrongPass123!')
    await user.type(getConfirmField(), 'StrongPass123!')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('shows password mismatch error', async () => {
    renderWithRouter(<RegisterPage />)

    await user.type(getNameField(), 'Alice')
    await user.type(getEmailField(), 'alice@example.com')
    await user.type(getPasswordField(), 'StrongPass123!')
    await user.type(getConfirmField(), 'DifferentPass!')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
  })

  it('shows short password error', async () => {
    renderWithRouter(<RegisterPage />)

    await user.type(getNameField(), 'Alice')
    await user.type(getEmailField(), 'alice@example.com')
    await user.type(getPasswordField(), 'short')
    await user.type(getConfirmField(), 'short')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(screen.getByText(/at least 8 characters/i)).toBeInTheDocument()
    })
  })

  it('calls register with correct data on valid submission', async () => {
    mockRegister.mockResolvedValue({ id: '1', email: 'alice@example.com' })

    renderWithRouter(<RegisterPage />)

    await user.type(getNameField(), 'Alice Dev')
    await user.type(getEmailField(), 'alice@example.com')
    await user.type(getPasswordField(), 'StrongPass123!')
    await user.type(getConfirmField(), 'StrongPass123!')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        first_name: 'Alice',
        last_name: 'Dev',
        email: 'alice@example.com',
        password: 'StrongPass123!',
      })
    })
  })

  it('has accessible form with correct input types', () => {
    renderWithRouter(<RegisterPage />)

    expect(getNameField()).toHaveAttribute('type', 'text')
    expect(getEmailField()).toHaveAttribute('type', 'email')
    expect(getPasswordField()).toHaveAttribute('type', 'password')
    expect(getConfirmField()).toHaveAttribute('type', 'password')
  })

  it('renders the register form with aria-label', () => {
    renderWithRouter(<RegisterPage />)

    const form = screen.getByRole('form', { name: /register form/i })
    expect(form).toBeInTheDocument()
  })
})
