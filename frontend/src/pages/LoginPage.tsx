/**
 * LoginPage — strict TypeScript, WCAG 2.1 AA accessible login form.
 *
 * Responsibilities (SRP):
 *  - Render login form with real-time validation
 *  - Handle 2FA modal flow
 *  - Delegate OAuth to OAuthButtons
 *  - Delegate auth side-effects to authStore
 */

import React, { useState, useEffect, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Lock, Mail, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react'

import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '../store/authStore'
import { FluidIcon } from '../components/UI'
import { Footer } from '../components/Footer'
import OAuthButtons from '../components/OAuthButtons'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { validateEmail } from '../utils/helpers'

// ── Types ──────────────────────────────────────────────────────────────────

interface LoginFormData {
  email: string
  password: string
}

interface LoginFormErrors {
  email?: string
  password?: string
}

interface TwoFactorVerifyResult {
  verified: boolean
}

// ── Animation variants ─────────────────────────────────────────────────────

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { type: 'spring' as const, stiffness: 100, damping: 20 },
  },
} as const

// ── Sub-components ─────────────────────────────────────────────────────────

interface ErrorBannerProps {
  message: string
  onDismiss: () => void
}

const ErrorBanner: React.FC<ErrorBannerProps> = ({ message, onDismiss }) => (
  <motion.div
    className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    role="alert"
    aria-live="assertive"
  >
    <FluidIcon icon={AlertCircle} size="sm" className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
    <div className="flex-1">
      <h3 className="font-semibold text-red-900 dark:text-red-300">Login Failed</h3>
      <p className="text-sm-fluid text-red-700 dark:text-red-400 mt-0.5">{message}</p>
    </div>
    <button
      onClick={onDismiss}
      className="text-red-600 hover:text-red-700 font-bold"
      type="button"
      aria-label="Dismiss error"
    >
      ×
    </button>
  </motion.div>
)

interface FieldErrorProps {
  message: string
}

const FieldError: React.FC<FieldErrorProps> = ({ message }) => (
  <motion.p
    className="text-sm-fluid text-red-600 mt-2 flex items-center gap-1"
    initial={{ opacity: 0, y: -5 }}
    animate={{ opacity: 1, y: 0 }}
    role="alert"
  >
    <FluidIcon icon={AlertCircle} size="sm" className="text-red-600 dark:text-red-400" />
    {message}
  </motion.p>
)

// ── Main component ─────────────────────────────────────────────────────────

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { login, isLoading, error, clearError } = useAuthStore()

  const [formData, setFormData] = useState<LoginFormData>({ email: '', password: '' })
  const [formErrors, setFormErrors] = useState<LoginFormErrors>({})
  const [showPassword, setShowPassword] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const [isValidating, setIsValidating] = useState(false)
  const [touched, setTouched] = useState<Partial<Record<keyof LoginFormData, boolean>>>({})

  const [twoFactorRequired, setTwoFactorRequired] = useState(false)
  const [twoFactorUserId, setTwoFactorUserId] = useState<number | null>(null)
  const [twoFactorCode, setTwoFactorCode] = useState('')

  // Real-time email validation with debounce
  useEffect(() => {
    if (!touched.email || !formData.email) return

    setIsValidating(true)
    const timer = setTimeout(() => {
      setFormErrors((prev) => ({
        ...prev,
        email: validateEmail(formData.email) ? '' : 'Invalid email format',
      }))
      setIsValidating(false)
    }, 300)
    return () => clearTimeout(timer)
  }, [formData.email, touched.email])

  const validateForm = useCallback((): LoginFormErrors => {
    const errors: LoginFormErrors = {}
    if (!formData.email) errors.email = 'Email is required'
    else if (!validateEmail(formData.email)) errors.email = 'Invalid email format'
    if (!formData.password) errors.password = 'Password is required'
    else if (formData.password.length < 6) errors.password = 'Password must be at least 6 characters'
    return errors
  }, [formData])

  const handleFieldChange = useCallback(
    (field: keyof LoginFormData) =>
      (e: ChangeEvent<HTMLInputElement>) => {
        setFormData((prev) => ({ ...prev, [field]: e.target.value }))
        setTouched((prev) => ({ ...prev, [field]: true }))
      },
    []
  )

  const redirectToDashboard = useCallback(() => {
    try {
      window.location.replace('/dashboard')
    } catch {
      navigate('/dashboard')
    }
  }, [navigate])

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      const errors = validateForm()
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors)
        return
      }

      try {
        const response = await login(formData)
        if (response?.requires_2fa) {
          setTwoFactorRequired(true)
          setTwoFactorUserId(response.user_id ?? null)
          return
        }
        showSuccessToast('Login successful!')
        redirectToDashboard()
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { requires_2fa?: boolean; user_id?: number } } }
        if (axiosErr.response?.data?.requires_2fa) {
          setTwoFactorRequired(true)
          setTwoFactorUserId(axiosErr.response.data.user_id ?? null)
          return
        }
        showErrorToast(error ?? 'Login failed')
      }
    },
    [formData, validateForm, login, error, redirectToDashboard]
  )

  const handleTwoFactorSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      if (!twoFactorCode || twoFactorCode.length < 6) {
        showErrorToast('Please enter a valid 6-digit code')
        return
      }
      try {
        const { twoFactorService } = await import('../services/apiService')
        const result = (await twoFactorService.verify(twoFactorUserId!, twoFactorCode)) as TwoFactorVerifyResult
        if (result.verified) {
          showSuccessToast('Login successful!')
          redirectToDashboard()
        }
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        showErrorToast(axiosErr.response?.data?.detail ?? '2FA verification failed')
        setTwoFactorCode('')
      }
    },
    [twoFactorCode, twoFactorUserId, redirectToDashboard]
  )

  const handleOAuthSuccess = useCallback(() => {
    showSuccessToast('Login successful!')
    redirectToDashboard()
  }, [redirectToDashboard])

  const emailFieldClass = [
    'w-full pl-10 pr-4 py-3 border-2 rounded-lg transition-all duration-200',
    'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none',
    focusedField === 'email'
      ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600'
      : formErrors.email
        ? 'border-red-300 bg-red-50 dark:bg-red-900/20'
        : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500',
  ].join(' ')

  const passwordFieldClass = [
    'w-full pl-10 pr-12 py-3 border-2 rounded-lg transition-all duration-200',
    'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none',
    focusedField === 'password'
      ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600'
      : formErrors.password
        ? 'border-red-300 bg-red-50 dark:bg-red-900/20'
        : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500',
  ].join(' ')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-slate-900 flex flex-col relative overflow-hidden">
      <div className="flex-1 flex flex-col items-center justify-center p-4 relative">
        {/* Desktop header: show logo + name + slogan with a Register link on md+ */}
        <header className="app-header auth-top-header hidden md:flex w-full mb-4">
          <div className="app-header-inner">
            <div className="flex items-center gap-3">
              <div className="hero-logo" style={{ width: 'var(--page-hero-icon-size)', height: 'var(--page-hero-icon-size)' }}>
                <img src={FinEdLogo} alt="FinEd logo" className="object-contain w-full h-full" />
              </div>
              <div className="text-left">
                <h1 className="text-heading-lg font-bold text-gray-900 dark:text-gray-100">FinEd</h1>
                <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Master Your Financial Future</p>
              </div>
            </div>
            <div className="flex items-center">
              <Link to="/register" className="text-sm-fluid text-indigo-600 hover:text-indigo-700 font-semibold">
                Register
              </Link>
            </div>
          </div>
        </header>

        {/* Mobile header: show a compact header with logo + title on small screens only */}
        <header className="auth-page-header mb-4 md:hidden">
          <div className="flex items-center justify-center gap-3">
            <div className="hero-logo" style={{ width: 'var(--page-hero-icon-size)', height: 'var(--page-hero-icon-size)' }}>
              <img src={FinEdLogo} alt="FinEd logo" className="object-contain w-full h-full" />
            </div>
            <div className="text-center">
              <h1 className="text-xl-fluid font-bold text-gray-900 dark:text-gray-100">FinEd</h1>
              <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Master Your Financial Future</p>
            </div>
          </div>
        </header>

        <div className="w-full">
          <div className="auth-split">
            {/* Left hero for md+ (half page) */}
            <div className="auth-left">
              <div className="hero-inner">
                <motion.div className="mb-6 auth-hero" variants={itemVariants}>
                  {/* Hero visuals removed from left column to keep focus on features + form (logo/title/strapline intentionally omitted) */}
                 </motion.div>

                <motion.div className="mt-4 text-left" variants={itemVariants}>
                  <h2 className="text-2xl-fluid font-bold text-gray-900 dark:text-gray-100">Welcome back</h2>
                  <p className="mt-2 text-sm-fluid text-gray-600 dark:text-gray-400">Sign in to continue to your dashboard</p>

                  {/* Features (moved from footer) */}
                  <div className="mt-4 text-sm text-gray-600 dark:text-gray-400">
                    <h3 className="font-semibold mb-2">Features</h3>
                    <ul className="space-y-1 list-inside">
                      <li>💸 Expense Tracking &amp; Categorisation</li>
                      <li>📊 Monthly Budget Management</li>
                      <li>🎯 Savings Goals</li>
                      <li>🏦 Loan &amp; EMI Calculator</li>
                      <li>📈 Financial Reports &amp; Analytics</li>
                      <li>🔔 Smart Notifications &amp; Alerts</li>
                      <li>🤖 AI-Powered Financial Chat</li>
                      <li>🔐 Two-Factor Authentication (2FA)</li>
                      <li>🇪🇺 GDPR Data Export &amp; Deletion</li>
                    </ul>
                  </div>
                </motion.div>
              </div>
            </div>

            {/* Right column — contains the auth form so on md+ screens the hero/features (left) and form (right) are side-by-side */}
            <div className="auth-right">
              <div className="mt-6 w-full">
                <motion.form
                  onSubmit={handleSubmit}
                  noValidate
                  aria-label="Login form"
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl dark:shadow-xl dark:shadow-black/20 p-6 space-y-4 auth-form"
                  variants={itemVariants}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  {/* Error Alert */}
                  <motion.div variants={itemVariants}>
                    {error && <ErrorBanner message={error} onDismiss={clearError} />}
                  </motion.div>

                  {/* Email Field */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="login-email" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Email Address
                    </label>
                    <motion.div
                      className="relative"
                      animate={{ boxShadow: focusedField === 'email' ? '0 0 0 3px rgba(79,70,229,0.1)' : '0 0 0 0px rgba(79,70,229,0)' }}
                    >
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true">
                        <FluidIcon icon={Mail} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        placeholder="you@example.com"
                        value={formData.email}
                        onChange={handleFieldChange('email')}
                        onFocus={() => setFocusedField('email')}
                        onBlur={() => setFocusedField(null)}
                        aria-invalid={!!formErrors.email}
                        aria-describedby={formErrors.email ? 'email-error' : undefined}
                        className={emailFieldClass}
                      />
                      {isValidating && focusedField === 'email' && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2" aria-hidden="true">
                          <motion.div
                            style={{ width: 'var(--spinner-sm)', height: 'var(--spinner-sm)' }}
                            className="border-2 border-indigo-300 rounded-full border-t-indigo-600"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          />
                        </div>
                      )}
                      {formData.email && !formErrors.email && !isValidating && (
                        <div className="absolute right-3 top-1/2 -translate-y-1/2" aria-hidden="true">
                          <FluidIcon icon={CheckCircle} size="sm" className="text-green-500" />
                        </div>
                      )}
                    </motion.div>
                    {formErrors.email && <FieldError message={formErrors.email} />}
                  </motion.div>

                  {/* Password Field */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="login-password" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Password
                    </label>
                    <motion.div
                      className="relative"
                      animate={{ boxShadow: focusedField === 'password' ? '0 0 0 3px rgba(79,70,229,0.1)' : '0 0 0 0px rgba(79,70,229,0)' }}
                    >
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden="true">
                        <FluidIcon icon={Lock} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        placeholder="••••••••"
                        value={formData.password}
                        onChange={handleFieldChange('password')}
                        onFocus={() => setFocusedField('password')}
                        onBlur={() => setFocusedField(null)}
                        aria-invalid={!!formErrors.password}
                        aria-describedby={formErrors.password ? 'password-error' : undefined}
                        className={passwordFieldClass}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      >
                        <FluidIcon icon={showPassword ? EyeOff : Eye} size="sm" className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" />
                      </button>
                    </motion.div>
                    {formErrors.password && <FieldError message={formErrors.password} />}
                  </motion.div>

                  {/* Remember + Forgot */}
                  <motion.div className="flex items-center justify-between" variants={itemVariants}>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" className="w-4 h-4 accent-indigo-600 rounded" />
                      <span className="text-sm-fluid text-gray-600 dark:text-gray-400">Remember me</span>
                    </label>
                    <Link to="/forgot-password" className="text-sm-fluid text-indigo-600 hover:text-indigo-700 font-semibold transition-colors">
                      Forgot password?
                    </Link>
                  </motion.div>

                  {/* Submit Button */}
                  <motion.button
                    type="submit"
                    disabled={isLoading}
                    aria-disabled={isLoading}
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold py-3 px-4 rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none flex items-center justify-center gap-2"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    variants={itemVariants}
                  >
                    {isLoading ? (
                      <>
                        <motion.div
                          className="border-2 border-white border-t-transparent rounded-full"
                          style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }}
                          animate={{ rotate: 360 }}
                          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          aria-hidden="true"
                        />
                        Signing in…
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </motion.button>

                  {/* Divider */}
                  <motion.div className="flex items-center gap-3" variants={itemVariants} aria-hidden="true">
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600" />
                    <span className="text-sm-fluid text-gray-500 dark:text-gray-400">or</span>
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600" />
                  </motion.div>

                  {/* OAuth Buttons */}
                  <motion.div variants={itemVariants} className="oauth-row">
                    <OAuthButtons
                      redirectUri={`${window.location.origin}/auth/callback`}
                      onSuccess={handleOAuthSuccess}
                      onError={(err: Error) => showErrorToast(err.message ?? 'OAuth login failed')}
                      compact={true}
                      showDivider={false}
                    />
                  </motion.div>
                </motion.form>
              </div>
            </div>
          </div>

          {/* 2FA Verification Modal */}
          {twoFactorRequired && (
            <motion.div
              className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              role="dialog"
              aria-modal="true"
              aria-label="Two-factor authentication"
            >
              <motion.form
                onSubmit={handleTwoFactorSubmit}
                className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 w-full space-y-5"
                style={{ maxWidth: 'var(--content-max-width)' }}
                initial={{ scale: 0.9, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
              >
                <div className="text-center">
                  <div
                    className="mx-auto rounded-full flex items-center justify-center mb-4"
                    style={{ width: 'calc(var(--icon-md) * 1.4)', height: 'calc(var(--icon-md) * 1.4)', backgroundColor: 'var(--icon-bg, #eef2ff)' }}
                  >
                    <FluidIcon icon={Lock} size="md" className="text-indigo-600 dark:text-indigo-400" />
                  </div>
                  <h2 className="text-xl-fluid font-bold text-gray-900 dark:text-gray-100">Two-Factor Verification</h2>
                  <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-1">Enter the 6-digit code from your authenticator app</p>
                </div>
                <label htmlFor="totp-code" className="sr-only">Authentication code</label>
                <input
                  id="totp-code"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  value={twoFactorCode}
                  onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="000000"
                  autoFocus
                  aria-label="6-digit authentication code"
                  className="w-full text-center text-2xl-fluid font-mono tracking-[0.5em] px-4 py-3 border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:border-indigo-500 focus:outline-none"
                />
                <button
                  type="submit"
                  disabled={twoFactorCode.length < 6}
                  className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-bold py-3 rounded-lg transition-colors"
                >
                  Verify
                </button>
                <button
                  type="button"
                  onClick={() => { setTwoFactorRequired(false); setTwoFactorCode('') }}
                  className="w-full text-sm-fluid text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
                >
                  Cancel
                </button>
              </motion.form>
            </motion.div>
          )}

          {/* footer is rendered globally via <Footer />; page-specific info moved into the hero */}
        </div>
      </div>
      <Footer />
    </div>
  )
}
