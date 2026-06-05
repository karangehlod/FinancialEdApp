/**
 * RegisterPage — strict TypeScript, WCAG 2.1 AA accessible registration form.
 *
 * Responsibilities (SRP):
 *  - Render registration form with real-time validation and password strength
 *  - Delegate auth to authStore
 *  - Delegate OAuth to OAuthButtons
 */

import React, { useState, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Lock, Mail, Eye, EyeOff, AlertCircle, CheckCircle, User } from 'lucide-react'

import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '../store/authStore'
import { FluidIcon } from '../components/UI'
import { Footer } from '../components/Footer'
import OAuthButtons from '../components/OAuthButtons'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { validateEmail } from '../utils/helpers'

// ── Types ──────────────────────────────────────────────────────────────────

interface RegisterFormData {
  name: string
  email: string
  password: string
  confirm_password: string
}

type RegisterFormErrors = Partial<Record<keyof RegisterFormData, string>>

type PasswordStrength = 0 | 1 | 2 | 3 | 4

// ── Helpers ────────────────────────────────────────────────────────────────

const getPasswordStrength = (password: string): PasswordStrength => {
  if (!password) return 0
  let strength = 0
  if (password.length >= 8) strength++
  if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++
  if (/\d/.test(password)) strength++
  if (/[!@#$%^&*]/.test(password)) strength++
  return strength as PasswordStrength
}

const strengthColorMap: Record<PasswordStrength, string> = {
  0: 'bg-gray-300',
  1: 'bg-red-400',
  2: 'bg-orange-400',
  3: 'bg-yellow-400',
  4: 'bg-green-400',
}

const strengthLabelMap: Record<PasswordStrength, string> = {
  0: '',
  1: 'Weak password',
  2: 'Fair password',
  3: 'Good password',
  4: '💪 Strong password',
}

// ── Animation variants ─────────────────────────────────────────────────────

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { type: 'spring' as const, stiffness: 100, damping: 20 } },
} as const

// ── Sub-components ─────────────────────────────────────────────────────────

interface FieldErrorProps {
  message: string
  id?: string
}

const FieldError: React.FC<FieldErrorProps> = ({ message, id }) => (
  <motion.p
    id={id}
    className="text-sm-fluid text-red-600 mt-2 flex items-center gap-1"
    initial={{ opacity: 0, y: -5 }}
    animate={{ opacity: 1, y: 0 }}
    role="alert"
  >
    <FluidIcon icon={AlertCircle} size="sm" className="text-red-600 dark:text-red-400" />
    {message}
  </motion.p>
)

interface PasswordStrengthBarProps {
  strength: PasswordStrength
}

const PasswordStrengthBar: React.FC<PasswordStrengthBarProps> = ({ strength }) => (
  <motion.div className="mt-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }} aria-live="polite">
    <div className="flex gap-1 mb-1" role="img" aria-label={`Password strength: ${strengthLabelMap[strength]}`}>
      {([0, 1, 2, 3] as const).map((i) => (
        <div
          key={i}
          className={`h-1 flex-1 rounded-full transition-all ${i < strength ? strengthColorMap[strength] : 'bg-gray-200'}`}
        />
      ))}
    </div>
    <p className="text-xs text-gray-500">{strengthLabelMap[strength]}</p>
  </motion.div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const { register, isLoading, error } = useAuthStore()

  const [formData, setFormData] = useState<RegisterFormData>({
    name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [formErrors, setFormErrors] = useState<RegisterFormErrors>({})
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [focusedField, setFocusedField] = useState<string | null>(null)
  const passwordStrength = getPasswordStrength(formData.password)

  const handleFieldChange = useCallback(
    (field: keyof RegisterFormData) =>
      (e: ChangeEvent<HTMLInputElement>) => {
        setFormData((prev) => ({ ...prev, [field]: e.target.value }))
      },
    []
  )

  const validateForm = useCallback((): RegisterFormErrors => {
    const errors: RegisterFormErrors = {}
    if (!formData.name) errors.name = 'Name is required'
    if (!formData.email) errors.email = 'Email is required'
    else if (!validateEmail(formData.email)) errors.email = 'Invalid email format'
    if (!formData.password) errors.password = 'Password is required'
    else if (formData.password.length < 8) errors.password = 'Password must be at least 8 characters'
    if (!formData.confirm_password) errors.confirm_password = 'Please confirm your password'
    else if (formData.password !== formData.confirm_password)
      errors.confirm_password = 'Passwords do not match'
    return errors
  }, [formData])

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      const errors = validateForm()
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors)
        return
      }

      try {
        await register({
          first_name: formData.name.split(' ')[0] ?? formData.name,
          last_name: formData.name.split(' ').slice(1).join(' ') || formData.name,
          email: formData.email,
          password: formData.password,
        })
        showSuccessToast('Registration successful! Please log in.')
        try {
          window.location.replace('/login')
        } catch {
          navigate('/login')
        }
      } catch {
        showErrorToast(error ?? 'Registration failed')
      }
    },
    [formData, validateForm, register, error, navigate]
  )

  const buildInputClass = (field: keyof RegisterFormData): string =>
    [
      'w-full pl-10 pr-4 py-3 border-2 rounded-lg transition-all duration-200 shadow-sm',
      'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none',
      focusedField === field
        ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
        : formErrors[field]
          ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
          : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500',
    ].join(' ')

  const passwordInputClass = (field: 'password' | 'confirm_password'): string =>
    [
      'w-full pl-10 pr-12 py-3 border-2 rounded-lg transition-all duration-200 shadow-sm',
      'bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-700',
      focusedField === field
        ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
        : formErrors[field]
          ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
          : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500',
    ].join(' ')

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-slate-900 flex flex-col relative overflow-hidden">
      <div className="flex-1 flex flex-col items-center justify-center p-4 relative">
        {/* Desktop header: show logo + name + slogan with a Login link on md+ */}
        <header className="app-header auth-top-header hidden md:flex w-full mb-4">
          <div className="app-header-inner">
            <div className="flex items-center gap-3">
              <div className="hero-logo" style={{ width: 'var(--page-hero-icon-size)', height: 'var(--page-hero-icon-size)' }}>
                <img src={FinEdLogo} alt="FinEd logo" className="object-contain w-full h-full" />
              </div>
              <div className="text-left">
                <h1 className="text-heading-lg font-bold text-gray-900 dark:text-gray-100">Create Account</h1>
                <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Join FinEd and start managing your finances</p>
              </div>
            </div>
            <div className="flex items-center">
              <Link to="/login" className="text-sm-fluid text-indigo-600 hover:text-indigo-700 font-semibold">
                Login
              </Link>
            </div>
          </div>
        </header>

        {/* Mobile header: compact header with logo + title for small screens */}
        <header className="auth-page-header mb-4 md:hidden">
          <div className="flex items-center justify-center gap-3">
            <div className="hero-logo" style={{ width: 'var(--page-hero-icon-size)', height: 'var(--page-hero-icon-size)' }}>
              <img src={FinEdLogo} alt="FinEd logo" className="object-contain w-full h-full" />
            </div>
            <div className="text-center">
              <h1 className="text-xl-fluid font-bold text-gray-900 dark:text-gray-100">Create Account</h1>
              <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Join FinEd and start managing your finances</p>
            </div>
          </div>
        </header>

        <div className="w-full">
          <div className="auth-split">
            <div className="auth-left">
              <div className="hero-inner">
                <motion.div className="mb-6 auth-hero" variants={itemVariants}>
                  {/* Hero visuals removed from left column to keep focus on features + form (logo/title/strapline intentionally omitted) */}
                </motion.div>

                {/* Moved form under hero and features so content is on the left */}
                <div className="mt-4 w-full">
                  {/* Features (moved from footer) */}
                  <motion.div className="mt-4 text-left" variants={itemVariants}>
                    <h3 className="font-semibold mb-2">Features</h3>
                    <ul className="space-y-1 text-sm text-gray-600 dark:text-gray-400 list-inside">
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
                  </motion.div>
                </div>
              </div>
            </div>

            {/* Right column — contains the register form so hero/features (left) and form (right) sit side-by-side on md+ */}
            <div className="auth-right">
              <div className="mt-4 w-full">
                <motion.form
                  onSubmit={handleSubmit}
                  noValidate
                  aria-label="Register form"
                  className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl dark:shadow-xl dark:shadow-black/20 p-6 space-y-4 auth-form"
                  variants={itemVariants}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                >
                  {/* Name Field */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="register-name" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Full name
                    </label>
                    <motion.div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden>
                        <FluidIcon icon={User} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="register-name"
                        type="text"
                        value={formData.name}
                        onChange={handleFieldChange('name')}
                        onFocus={() => setFocusedField('name')}
                        onBlur={() => setFocusedField(null)}
                        className={buildInputClass('name')}
                        placeholder="Your full name"
                      />
                    </motion.div>
                    {formErrors.name && <FieldError id="name-error" message={formErrors.name} />}
                  </motion.div>

                  {/* Email */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="register-email" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Email
                    </label>
                    <motion.div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden>
                        <FluidIcon icon={Mail} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="register-email"
                        type="email"
                        value={formData.email}
                        onChange={handleFieldChange('email')}
                        onFocus={() => setFocusedField('email')}
                        onBlur={() => setFocusedField(null)}
                        className={buildInputClass('email')}
                        placeholder="you@example.com"
                      />
                    </motion.div>
                    {formErrors.email && <FieldError id="email-error" message={formErrors.email} />}
                  </motion.div>

                  {/* Password */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="register-password" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Password
                    </label>
                    <motion.div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden>
                        <FluidIcon icon={Lock} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="register-password"
                        type={showPassword ? 'text' : 'password'}
                        value={formData.password}
                        onChange={handleFieldChange('password')}
                        onFocus={() => setFocusedField('password')}
                        onBlur={() => setFocusedField(null)}
                        className={passwordInputClass('password')}
                        placeholder="Choose a strong password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((v) => !v)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      >
                        <FluidIcon icon={showPassword ? EyeOff : Eye} size="sm" className="text-gray-400" />
                      </button>
                    </motion.div>
                    {formErrors.password && <FieldError id="password-error" message={formErrors.password} />}
                    <PasswordStrengthBar strength={passwordStrength} />
                  </motion.div>

                  {/* Confirm Password */}
                  <motion.div variants={itemVariants}>
                    <label htmlFor="register-confirm" className="block text-sm-fluid font-semibold text-gray-900 dark:text-gray-200 mb-2">
                      Confirm password
                    </label>
                    <motion.div className="relative">
                      <div className="absolute left-3 top-1/2 -translate-y-1/2" aria-hidden>
                        <FluidIcon icon={Lock} size="sm" className="text-gray-400 dark:text-gray-500" />
                      </div>
                      <input
                        id="register-confirm"
                        type={showConfirmPassword ? 'text' : 'password'}
                        value={formData.confirm_password}
                        onChange={handleFieldChange('confirm_password')}
                        onFocus={() => setFocusedField('confirm_password')}
                        onBlur={() => setFocusedField(null)}
                        className={passwordInputClass('confirm_password')}
                        placeholder="Confirm your password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((v) => !v)}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      >
                        <FluidIcon icon={showConfirmPassword ? EyeOff : Eye} size="sm" className="text-gray-400" />
                      </button>
                    </motion.div>
                    {formErrors.confirm_password && <FieldError id="confirm-error" message={formErrors.confirm_password} />}
                  </motion.div>

                  <motion.button
                    type="submit"
                    className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 rounded-lg"
                    disabled={isLoading}
                  >
                    {isLoading ? 'Creating…' : 'Create account'}
                  </motion.button>

                  <motion.div className="flex items-center gap-3" variants={itemVariants} aria-hidden>
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                    <span className="text-sm-fluid text-gray-500 dark:text-gray-400">or</span>
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                  </motion.div>

                  <motion.div variants={itemVariants} className="oauth-row">
                    <OAuthButtons
                      redirectUri={`${window.location.origin}/auth/callback`}
                      compact={true}
                      showDivider={false}
                      onSuccess={() => showSuccessToast('Account created - please log in')}
                      onError={(e: Error) => showErrorToast(e.message)}
                    />
                  </motion.div>
                </motion.form>
              </div>
            </div>
          </div>

          {/* Footer Info */}
          <motion.div className="mt-8 text-center text-sm-fluid text-gray-600 dark:text-gray-400" variants={itemVariants}>
            <p>🔒 Your data is secure and encrypted</p>
          </motion.div>
        </div>
      </div>
      <Footer />
    </div>
  )
}
