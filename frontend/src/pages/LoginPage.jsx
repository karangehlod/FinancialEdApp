import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Lock, Mail, Eye, EyeOff, AlertCircle, CheckCircle, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react'
import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '../store/authStore'
import { Footer } from '../components/Footer'
import OAuthButtons from '../components/OAuthButtons'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { validateEmail } from '../utils/helpers'

export const LoginPage = () => {
  const navigate = useNavigate()
  const { login, isLoading, error, clearError } = useAuthStore()
  const [formData, setFormData] = useState({ email: '', password: '' })
  const [formErrors, setFormErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [focusedField, setFocusedField] = useState(null)
  const [isValidating, setIsValidating] = useState(false)
  const [touched, setTouched] = useState({})

  const [twoFactorRequired, setTwoFactorRequired] = useState(false)
  const [twoFactorUserId, setTwoFactorUserId] = useState(null)
  const [twoFactorCode, setTwoFactorCode] = useState('')

  // Real-time validation
  useEffect(() => {
    if (touched.email && formData.email) {
      setIsValidating(true)
      const timer = setTimeout(() => {
        if (!validateEmail(formData.email)) {
          setFormErrors((prev) => ({ ...prev, email: 'Invalid email format' }))
        } else {
          setFormErrors((prev) => ({ ...prev, email: '' }))
        }
        setIsValidating(false)
      }, 300)
      return () => clearTimeout(timer)
    }
  }, [formData.email, touched.email])

  const validateForm = () => {
    const errors = {}
    if (!formData.email) errors.email = 'Email is required'
    else if (!validateEmail(formData.email)) errors.email = 'Invalid email format'
    if (!formData.password) errors.password = 'Password is required'
    else if (formData.password.length < 6) errors.password = 'Password must be at least 6 characters'
    return errors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errors = validateForm()

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }

    try {
      const response = await login(formData)
      // Check if 2FA is required
      if (response?.requires_2fa) {
        setTwoFactorRequired(true)
        setTwoFactorUserId(response.user_id)
        return
      }
      showSuccessToast('Login successful!')
      try {
        // Hard redirect to ensure the app reloads with fresh auth state
        window.location.replace('/dashboard')
      } catch (err) {
        navigate('/dashboard')
      }
    } catch (err) {
      // Backend might return 2FA required in error response
      if (err.response?.data?.requires_2fa) {
        setTwoFactorRequired(true)
        setTwoFactorUserId(err.response.data.user_id)
        return
      }
      showErrorToast(error || 'Login failed')
    }
  }

  const handleTwoFactorSubmit = async (e) => {
    e.preventDefault()
    if (!twoFactorCode || twoFactorCode.length < 6) {
      showErrorToast('Please enter a valid 6-digit code')
      return
    }
    try {
      const { twoFactorService } = await import('../services/apiService')
      const result = await twoFactorService.verify(twoFactorUserId, twoFactorCode)
      if (result.verified) {
        showSuccessToast('Login successful!')
        try {
          window.location.replace('/dashboard')
        } catch (err) {
          navigate('/dashboard')
        }
      }
    } catch (err) {
      showErrorToast(err.response?.data?.detail || '2FA verification failed')
      setTwoFactorCode('')
    }
  }

  const handleOAuthSuccess = () => {
    showSuccessToast('Login successful!')
    try {
      window.location.replace('/dashboard')
    } catch (err) {
      navigate('/dashboard')
    }
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1,
        delayChildren: 0.2,
      },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { type: 'spring', stiffness: 100, damping: 20 },
    },
  }

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#fff8e7_0%,#f7f9fc_38%,#e8eefc_100%)] dark:bg-[radial-gradient(circle_at_top,#1f2937_0%,#111827_42%,#030712_100%)] flex flex-col relative overflow-hidden">
      <div className="flex-1 flex items-center justify-center px-4 py-8 sm:px-6 lg:px-8 relative">
      {/* Animated Background Blobs */}
      <motion.div
        className="absolute -top-16 -right-10 rounded-full blur-3xl opacity-30 pointer-events-none"
        style={{ width: 'var(--bg-blob-size)', height: 'var(--bg-blob-size)', backgroundColor: 'var(--bg-blob-primary, #fdba74)' }}
        animate={{ y: [0, 100, 0], x: [0, 50, 0] }}
        transition={{ duration: 15, repeat: Infinity }}
      />
      <motion.div
        className="absolute -bottom-16 -left-10 rounded-full blur-3xl opacity-25 pointer-events-none"
        style={{ width: 'var(--bg-blob-size)', height: 'var(--bg-blob-size)', backgroundColor: 'var(--bg-blob-secondary, #7dd3fc)' }}
        animate={{ y: [0, -100, 0], x: [0, -50, 0] }}
        transition={{ duration: 20, repeat: Infinity }}
      />
      <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(to_right,rgba(15,23,42,0.04)_1px,transparent_1px),linear-gradient(to_bottom,rgba(15,23,42,0.04)_1px,transparent_1px)] bg-[size:36px_36px] dark:bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)]" />

      {/* Main Content */}
      <motion.div
        className="relative z-10 w-full max-w-6xl"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <div className="grid items-center gap-8 lg:grid-cols-[1.05fr_minmax(0,480px)]">
          <motion.section
            className="hidden lg:block"
            variants={itemVariants}
          >
            <div className="max-w-xl">
              <motion.div
                className="inline-flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-4 py-2 text-sm font-medium text-slate-700 shadow-sm backdrop-blur dark:border-white/10 dark:bg-slate-900/50 dark:text-slate-200"
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                <Sparkles size={16} />
                Personal finance, without the noise
              </motion.div>

              <div className="mt-8 flex items-center gap-5">
                <div
                  className="flex-shrink-0 rounded-[28px] bg-white/85 dark:bg-slate-900/70 flex items-center justify-center ring-1 ring-slate-200/70 dark:ring-white/10"
                  style={{
                    width: 'calc(var(--page-hero-icon-size) * 0.95)',
                    height: 'calc(var(--page-hero-icon-size) * 0.95)',
                    boxShadow: '0 24px 60px rgba(15,23,42,0.18)',
                  }}
                >
                  <img src={FinEdLogo} alt="FinEd" style={{ width: '72%', height: '72%' }} className="object-contain" />
                </div>

                <div>
                  <motion.h1 className="font-bold text-slate-900 dark:text-slate-100 leading-tight" style={{ fontSize: 'clamp(2.4rem, 4vw, 4.6rem)' }} variants={itemVariants}>
                    FinEd
                  </motion.h1>
                  <motion.p className="mt-2 max-w-md text-lg text-slate-600 dark:text-slate-300" variants={itemVariants}>
                    A focused space to track spending, stay accountable, and make better money decisions.
                  </motion.p>
                </div>
              </div>

              <div className="mt-10 grid gap-4 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-lg shadow-slate-200/40 backdrop-blur dark:border-white/10 dark:bg-slate-900/45 dark:shadow-none">
                  <ShieldCheck className="text-emerald-600 dark:text-emerald-400" size={20} />
                  <h2 className="mt-4 text-base font-semibold text-slate-900 dark:text-slate-100">Secure sign-in</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">Encrypted sessions, OAuth support, and optional 2FA for account protection.</p>
                </div>
                <div className="rounded-2xl border border-white/70 bg-white/70 p-5 shadow-lg shadow-slate-200/40 backdrop-blur dark:border-white/10 dark:bg-slate-900/45 dark:shadow-none">
                  <ArrowRight className="text-sky-600 dark:text-sky-400" size={20} />
                  <h2 className="mt-4 text-base font-semibold text-slate-900 dark:text-slate-100">Fast path back in</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">A cleaner form, clear validation, and demo access when you just want to explore.</p>
                </div>
              </div>
            </div>
          </motion.section>

          <motion.div
            className="mx-auto w-full max-w-[480px]"
            variants={itemVariants}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="rounded-[32px] border border-white/70 bg-white/88 p-6 shadow-[0_30px_80px_rgba(15,23,42,0.18)] backdrop-blur-xl dark:border-white/10 dark:bg-slate-900/80 dark:shadow-[0_30px_80px_rgba(0,0,0,0.45)] sm:p-8">
              <div className="mb-8 text-center lg:hidden">
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-3xl bg-white shadow-lg ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-white/10">
                  <img src={FinEdLogo} alt="FinEd" className="h-14 w-14 object-contain" />
                </div>
                <h1 className="mt-4 text-3xl font-bold text-slate-900 dark:text-slate-100">Welcome back</h1>
                <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">Sign in to continue managing your financial plan.</p>
              </div>

              <div className="mb-8 hidden lg:block">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-slate-500 dark:text-slate-400">Welcome back</p>
                <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-slate-100">Sign in to your account</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">Use your email and password, or continue with a connected provider.</p>
              </div>

              <motion.form onSubmit={handleSubmit} className="space-y-6">
          {/* Error Alert */}
          <motion.div variants={itemVariants}>
            {error && (
              <motion.div
                className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-red-900 dark:text-red-300">Login Failed</h3>
                  <p className="text-sm text-red-700 dark:text-red-400 mt-0.5">{error}</p>
                </div>
                <button
                  onClick={clearError}
                  className="text-red-600 hover:text-red-700 font-bold"
                  type="button"
                >
                  ×
                </button>
              </motion.div>
            )}
          </motion.div>

          {/* Email Input */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-200 mb-2">
              Email Address
            </label>
            <motion.div
              className="relative"
              animate={{
                boxShadow:
                  focusedField === 'email'
                    ? '0 0 0 3px rgba(79, 70, 229, 0.1)'
                    : '0 0 0 0px rgba(79, 70, 229, 0)',
              }}
            >
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500">
                <Mail size={20} />
              </div>
              <input
                type="email"
                placeholder="you@example.com"
                value={formData.email}
                onChange={(e) => {
                  setFormData({ ...formData, email: e.target.value })
                  setTouched({ ...touched, email: true })
                }}
                onFocus={() => setFocusedField('email')}
                onBlur={() => setFocusedField(null)}
                className={`w-full pl-10 pr-4 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                  focusedField === 'email'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600'
                    : formErrors.email
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none`}
              />
              {isValidating && focusedField === 'email' && (
                <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                  <motion.div
                    style={{ width: 'var(--spinner-sm)', height: 'var(--spinner-sm)' }}
                    className="border-2 border-indigo-300 rounded-full border-t-indigo-600"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity }}
                  />
                </div>
              )}
              {formData.email && !formErrors.email && !isValidating && (
                <CheckCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="absolute right-3 top-1/2 transform -translate-y-1/2 text-green-500" />
              )}
            </motion.div>
            {formErrors.email && (
              <motion.p
                className="text-sm text-red-600 mt-2 flex items-center gap-1"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={14} />
                {formErrors.email}
              </motion.p>
            )}
          </motion.div>

          {/* Password Input */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-200 mb-2">
              Password
            </label>
            <motion.div
              className="relative"
              animate={{
                boxShadow:
                  focusedField === 'password'
                    ? '0 0 0 3px rgba(79, 70, 229, 0.1)'
                    : '0 0 0 0px rgba(79, 70, 229, 0)',
              }}
            >
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500">
                <Lock size={20} />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.password}
                onChange={(e) => {
                  setFormData({ ...formData, password: e.target.value })
                  setTouched({ ...touched, password: true })
                }}
                onFocus={() => setFocusedField('password')}
                onBlur={() => setFocusedField(null)}
                className={`w-full pl-10 pr-12 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 ${
                  focusedField === 'password'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600'
                    : formErrors.password
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </motion.div>
            {formErrors.password && (
              <motion.p
                className="text-sm text-red-600 mt-2 flex items-center gap-1"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={14} />
                {formErrors.password}
              </motion.p>
            )}
          </motion.div>

          {/* Remember Me */}
          <motion.div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" variants={itemVariants}>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="w-4 h-4 accent-indigo-600 rounded cursor-pointer"
              />
              <span className="text-sm text-gray-600 dark:text-gray-400">Remember me</span>
            </label>
            <Link
              to="/forgot-password"
              className="text-sm text-indigo-600 hover:text-indigo-700 font-semibold transition-colors"
            >
              Forgot password?
            </Link>
          </motion.div>

          {/* Submit Button */}
          <motion.button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold py-3 px-4 rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none flex items-center justify-center gap-2"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            variants={itemVariants}
          >
            {isLoading ? (
              <>
                <motion.div
                  className="border-2 border-white border-t-transparent rounded-full" style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }}
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                Signing in...
              </>
            ) : (
              'Sign In'
            )}
          </motion.button>

          {/* Divider */}
          <motion.div className="hidden items-center gap-3" variants={itemVariants}>
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600"></div>
            <span className="text-sm text-gray-500 dark:text-gray-400">or</span>
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600"></div>
          </motion.div>

          {/* OAuth Buttons */}
          <motion.div variants={itemVariants}>
            <OAuthButtons
              redirectUri={`${window.location.origin}/auth/callback`}
              onSuccess={handleOAuthSuccess}
              onError={(err) => showErrorToast(err.message || 'OAuth login failed')}
            />
          </motion.div>

          {/* Sign Up Link */}
          <motion.div className="text-center border-t border-slate-200/80 pt-2 dark:border-slate-700/70" variants={itemVariants}>
            <p className="text-gray-600 dark:text-gray-400">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="text-indigo-600 hover:text-indigo-700 font-bold transition-colors"
              >
                Create one now
              </Link>
            </p>
          </motion.div>

        </motion.form>
            </div>
          </motion.div>
        </div>

        {/* 2FA Verification Modal */}
        {twoFactorRequired && (
          <motion.div
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <motion.form
              onSubmit={handleTwoFactorSubmit}
              className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl p-8 w-full space-y-5"
              style={{ maxWidth: 'var(--content-max-width)' }}
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
            >
              <div className="text-center">
                <div className="mx-auto rounded-full flex items-center justify-center mb-4" style={{ width: 'calc(var(--icon-md) * 1.4)', height: 'calc(var(--icon-md) * 1.4)', backgroundColor: 'var(--icon-bg, #eef2ff)' }}>
                  <Lock className="w-[calc(var(--icon-md) * 0.9)] h-[calc(var(--icon-md) * 0.9)] text-indigo-600 dark:text-indigo-400" />
                </div>
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Two-Factor Verification</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Enter the 6-digit code from your authenticator app</p>
              </div>
              <input
                type="text"
                inputMode="numeric"
                maxLength={6}
                value={twoFactorCode}
                onChange={(e) => setTwoFactorCode(e.target.value.replace(/\D/g, ''))}
                placeholder="000000"
                className="w-full text-center text-2xl font-mono tracking-[0.5em] px-4 py-3 border-2 border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-lg focus:border-indigo-500 focus:outline-none"
                autoFocus
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
                className="w-full text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300"
              >
                Cancel
              </button>
            </motion.form>
          </motion.div>
        )}
      </motion.div>
      </div>{/* end flex-1 center */}
      <Footer />
    </div>
  )
}
