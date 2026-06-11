import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { LoginPage } from '../pages/LoginPage'
import { useAuthStore } from '../store/authStore'

const mockReplace = vi.fn()

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
    logout: vi.fn(),
    clearError: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
    Object.defineProperty(window, 'location', {
      configurable: true,
      value: { replace: mockReplace },
    })
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

    expect(screen.getByPlaceholderText(/you@example.com/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/••••••••/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('submits form with email and password', async () => {
    mockLogin.mockResolvedValue({ success: true })
    renderLoginPage()

    const emailInput = screen.getByPlaceholderText(/you@example.com/i)
    const passwordInput = screen.getByPlaceholderText(/••••••••/i)
    const submitButton = screen.getByRole('button', { name: /sign in/i })

    fireEvent.change(emailInput, { target: { value: 'test@example.com' } })
    fireEvent.change(passwordInput, { target: { value: 'password123' } })
    fireEvent.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({ email: 'test@example.com', password: 'password123' })
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
      expect(screen.getByText(/invalid email format/i)).toBeInTheDocument()
    })

    expect(mockLogin).not.toHaveBeenCalled()
  })

  it('redirects to dashboard after successful login', async () => {
    mockLogin.mockResolvedValue({ success: true })

    renderLoginPage()

    fireEvent.change(screen.getByPlaceholderText(/you@example.com/i), {
      target: { value: 'test@example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText(/••••••••/i), {
      target: { value: 'password123' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith('/dashboard')
    })
  })

  it('has register link that navigates to register page', () => {
    renderLoginPage()

    const registerLink = screen.getByRole('link', { name: /create one now/i })
    expect(registerLink).toBeInTheDocument()
    expect(registerLink.closest('a')).toHaveAttribute('href', '/register')
  })
})
