import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from '../pages/LoginPage'
import { useAuthStore } from '../store/authStore'

// Mock the auth store
vi.mock('../store/authStore', () => ({
  useAuthStore: vi.fn(),
}))

// Mock react-router-dom
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useLocation: () => ({ state: {} }),
  }
})

describe('LoginPage', () => {
  const mockLogin = vi.fn()
  const defaultAuthStore = {
    login: mockLogin,
    isLoading: false,
    error: null,
    isAuthenticated: false,
    logout: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.mockReturnValue(defaultAuthStore)
  })

  const renderLoginPage = () => {
    return render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    )
  }

  it('renders login form with email and password fields', () => {
    renderLoginPage()

    // Inputs use placeholders in the markup — use those to locate elements
    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('submits form with email and password', async () => {
    mockLogin.mockResolvedValue({ success: true })
    renderLoginPage()

    const emailInput = screen.getByPlaceholderText(/you@example.com/i)
    const passwordInput = screen.getByPlaceholderText(/password/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123')
    })
  })

  it('displays loading state during login', () => {
    useAuthStore.mockReturnValue({
      ...defaultAuthStore,
      isLoading: true,
    })

    renderLoginPage()

    expect(screen.getByRole('button', { name: /signing in/i })).toBeDisabled()
  })

  it('displays error message on login failure', () => {
    useAuthStore.mockReturnValue({
      ...defaultAuthStore,
      error: 'Invalid credentials',
    })

    renderLoginPage()

    expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    renderLoginPage()

    const submitButton = screen.getByRole('button', { name: /sign in/i })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/email is required/i)).toBeInTheDocument()
      expect(screen.getByText(/password is required/i)).toBeInTheDocument()
    })

    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('validates email format', async () => {
    renderLoginPage()

    const emailInput = screen.getByPlaceholderText(/you@example.com/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(emailInput, { target: { value: 'invalid-email' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/please enter a valid email/i)).toBeInTheDocument()
    })

    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('redirects to dashboard after successful login', async () => {
    mockLogin.mockResolvedValue({ success: true })
    useAuthStore.mockReturnValue({
      ...defaultAuthStore,
      isAuthenticated: true,
    })

    renderLoginPage()

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard', { replace: true })
    })
  })

  it('has register link that navigates to register page', () => {
    renderLoginPage()

    // Some layouts render the register link as 'Create one here' or similar
    const registerLink = screen.queryByText(/create one here/i) || screen.queryByText(/register now/i) || screen.queryByText(/create an account/i) || screen.getByRole('link', { name: /register/i })
    expect(registerLink).toBeInTheDocument()
    expect(registerLink.closest('a')).toHaveAttribute('href', '/register')
  })
})
