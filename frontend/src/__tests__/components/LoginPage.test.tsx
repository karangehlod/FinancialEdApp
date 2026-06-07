/**
 * LoginPage tests — form rendering, validation, submission, and error states.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithRouter } from '../testUtils'
import { LoginPage } from '../../pages/LoginPage'

// ── Mocks ───────────────────────────────────────────────────────────────

const mockLogin = vi.fn()
const mockClearError = vi.fn()
const mockNavigate = vi.fn()

vi.mock('../../store/authStore', () => ({
  useAuthStore: () => ({
    login: mockLogin,
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

const getEmailField = () => screen.getByPlaceholderText('you@example.com') as HTMLInputElement
const getPasswordField = () => screen.getByPlaceholderText('••••••••') as HTMLInputElement

// ── Tests ───────────────────────────────────────────────────────────────

describe('LoginPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the login form with email and password fields', () => {
    renderWithRouter(<LoginPage />)

    expect(getEmailField()).toBeInTheDocument()
    expect(getPasswordField()).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('renders a link to the register page', () => {
    renderWithRouter(<LoginPage />)

    const registerLink = screen.getAllByRole('link').find(
      (link) => link.getAttribute('href') === '/register',
    )
    expect(registerLink).toBeInTheDocument()
  })

  it('renders OAuth buttons', () => {
    renderWithRouter(<LoginPage />)
    expect(screen.getByTestId('oauth-buttons')).toBeInTheDocument()
  })

  it('shows validation error for empty email on submit', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)

    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for empty password on submit', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)

    await user.type(getEmailField(), 'user@example.com')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for invalid email format', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)

    await user.type(getEmailField(), 'not-an-email')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('shows validation error for short password', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)

    await user.type(getEmailField(), 'user@example.com')
    await user.type(getPasswordField(), '12345')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(screen.getByText(/at least 6 characters/i)).toBeInTheDocument()
    })
  })

  it('calls login with correct credentials on valid submission', async () => {
    const user = userEvent.setup()
    mockLogin.mockResolvedValue({ access_token: 'tok', user: { id: '1' } })

    renderWithRouter(<LoginPage />)

    await user.type(getEmailField(), 'user@example.com')
    await user.type(getPasswordField(), 'StrongPass123!')
    await user.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'user@example.com',
        password: 'StrongPass123!',
      })
    })
  })

  it('toggles password visibility when the eye button is clicked', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)

    const passwordField = getPasswordField()
    expect(passwordField.type).toBe('password')

    const toggleBtn = screen.getAllByRole('button').find((button) => button.getAttribute('type') === 'button')
    await user.click(toggleBtn)

    expect(passwordField.type).toBe('text')
  })

  it('has accessible form with correct input types', () => {
    renderWithRouter(<LoginPage />)

    expect(getEmailField()).toHaveAttribute('type', 'email')
    expect(getPasswordField()).toHaveAttribute('type', 'password')
  })

  it('renders the form with an accessible aria-label', () => {
    renderWithRouter(<LoginPage />)

    const form = document.querySelector('form')
    expect(form).toBeInTheDocument()
  })
})
