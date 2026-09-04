import React, { useState, useEffect, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Lock, Mail, Eye, EyeOff, AlertCircle, ChevronRight,
  TrendingUp, PiggyBank, Target, BarChart2,
  Bell, MessageSquare, Shield, Zap, FileDown, RefreshCw,
} from 'lucide-react'

import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '@/store/authStore'
import OAuthButtons from '@/components/OAuthButtons'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import { validateEmail } from '@/utils/helpers'
import { Footer } from '@/components/Footer'

// ── Feature list — real app capabilities only ─────────────────────────────

const FEATURES = [
  { icon: TrendingUp,    label: 'Expense Tracking & Categorisation' },
  { icon: PiggyBank,     label: 'Monthly Budget Management' },
  { icon: Target,        label: 'Savings Goals with Progress Tracking' },
  { icon: Zap,           label: 'Loan Management & EMI Calculator' },
  { icon: BarChart2,     label: 'Financial Reports & Analytics' },
  { icon: Bell,          label: 'Smart Budget & Goal Alerts' },
  { icon: MessageSquare, label: 'AI-Powered Financial Assistant' },
  { icon: Shield,        label: 'Two-Factor Authentication (2FA)' },
  { icon: RefreshCw,     label: 'Multi-Currency Support' },
  { icon: FileDown,      label: 'CSV / JSON Data Export' },
]

const fade = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } }

// ── Component ──────────────────────────────────────────────────────────────

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const { login, isLoading, error, clearError } = useAuthStore()

  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [emailErr, setEmailErr] = useState('')
  const [passwordErr, setPasswordErr] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [touched, setTouched]   = useState({ email: false, password: false })

  const [need2FA, setNeed2FA]   = useState(false)
  const [code2FA, setCode2FA]   = useState('')

  useEffect(() => {
    if (!touched.email || !email) return
    const t = setTimeout(() => {
      setEmailErr(validateEmail(email) ? '' : 'Invalid email format')
    }, 300)
    return () => clearTimeout(t)
  }, [email, touched.email])

  const validate = useCallback(() => {
    const errs: { email?: string; password?: string } = {}
    if (!email)                      errs.email    = 'Email is required'
    else if (!validateEmail(email))  errs.email    = 'Invalid email format'
    if (!password)                   errs.password = 'Password is required'
    else if (password.length < 6)    errs.password = 'Minimum 6 characters'
    return errs
  }, [email, password])

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    const errs = validate()
    setEmailErr(errs.email ?? '')
    setPasswordErr(errs.password ?? '')
    if (errs.email || errs.password) return
    try {
      const res = await login({ email, password })
      if (res?.requires_2fa) { setNeed2FA(true); return }
      showSuccessToast('Welcome back!')
      navigate('/dashboard')
    } catch {
      showErrorToast(error ?? 'Login failed. Please try again.')
    }
  }, [email, password, validate, login, error, clearError, navigate])

  const handle2FA = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    if (code2FA.length < 6) { showErrorToast('Enter a valid 6-digit code'); return }
    try {
      const { twoFactorService } = await import('@/services/apiService')
      const result = await twoFactorService.verify(null, code2FA) as { verified: boolean }
      if (result.verified) { showSuccessToast('Login successful!'); navigate('/dashboard') }
    } catch {
      showErrorToast('Invalid 2FA code')
      setCode2FA('')
    }
  }, [code2FA, navigate])

  return (
    <div className="min-h-screen flex flex-col bg-gray-50 dark:bg-gray-950">

      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 flex items-center gap-3 px-6 py-4
                         bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800
                         shadow-sm">
        <img src={FinEdLogo} alt="FinEd" className="w-10 h-10 rounded-xl object-contain" />
        <div>
          <span className="font-bold text-lg text-gray-900 dark:text-white leading-tight block">FinEd</span>
          <span className="text-xs text-gray-500 dark:text-gray-400 leading-tight">Master Your Financial Future</span>
        </div>
      </header>

      {/* ── Main ────────────────────────────────────────────────────────── */}
      <main className="flex-1 flex items-start justify-center px-4 py-8 sm:py-12">
        <motion.div
          className="w-full max-w-5xl rounded-2xl shadow-2xl overflow-hidden
                     border border-gray-200 dark:border-gray-800
                     flex flex-col lg:flex-row"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >

          {/* ── Left panel — brand + features ──────────────────────────── */}
          <div className="lg:w-[42%] flex-shrink-0 flex flex-col
                          bg-gradient-to-br from-indigo-700 via-indigo-600 to-purple-700
                          p-8 xl:p-10 text-white">

            {/* Brand */}
            <div className="flex items-center gap-4 mb-8">
              <img
                src={FinEdLogo}
                alt="FinEd logo"
                className="w-16 h-16 rounded-2xl object-contain bg-white/10 p-1 shadow-lg"
              />
              <div>
                <p className="font-extrabold text-2xl leading-tight">FinEd</p>
                <p className="text-indigo-200 text-sm leading-tight">Master Your Financial Future</p>
              </div>
            </div>

            {/* Headline */}
            <div className="mb-6">
              <h2 className="text-2xl xl:text-3xl font-extrabold leading-snug">
                Take control of your financial future today.
              </h2>
              <p className="mt-3 text-indigo-200 text-sm leading-relaxed">
                Track every rupee, hit every goal, and get AI-powered advice — all in one place.
              </p>
            </div>

            {/* Features — real capabilities only */}
            <ul className="space-y-2.5 flex-1">
              {FEATURES.map(({ icon: Icon, label }) => (
                <li key={label} className="flex items-center gap-3 text-sm">
                  <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-white/15 flex items-center justify-center">
                    <Icon size={14} />
                  </span>
                  <span className="text-indigo-100">{label}</span>
                </li>
              ))}
            </ul>

            <p className="mt-8 text-indigo-300 text-xs">
              © {new Date().getFullYear()} FinancialEdApp · Built by Karan Gehlod
            </p>
          </div>

          {/* ── Right panel — form ─────────────────────────────────────── */}
          <div className="flex-1 bg-white dark:bg-gray-900 flex flex-col justify-center
                          px-6 py-8 sm:px-10 xl:px-12">

            <AnimatePresence mode="wait">

              {/* ── 2FA step ── */}
              {need2FA ? (
                <motion.div key="2fa" variants={fade} initial="hidden" animate="show">
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">Two-Factor Auth</h2>
                  <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
                    Enter the 6-digit code from your authenticator app.
                  </p>
                  <form onSubmit={handle2FA} noValidate className="space-y-4">
                    <input
                      type="text"
                      inputMode="numeric"
                      maxLength={6}
                      placeholder="000000"
                      value={code2FA}
                      onChange={(e) => setCode2FA(e.target.value.replace(/\D/g, ''))}
                      className="w-full text-center text-2xl tracking-widest font-mono
                                 px-4 py-3 rounded-xl border-2 border-gray-200 dark:border-gray-700
                                 bg-gray-50 dark:bg-gray-800 text-gray-900 dark:text-white
                                 focus:outline-none focus:border-indigo-500 transition"
                    />
                    <button type="submit"
                      className="w-full py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700
                                 text-white font-semibold text-sm transition">
                      Verify Code
                    </button>
                    <button type="button" onClick={() => setNeed2FA(false)}
                      className="w-full text-sm text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
                      ← Back to login
                    </button>
                  </form>
                </motion.div>

              ) : (

                /* ── Login step ── */
                <motion.div key="login" variants={fade} initial="hidden" animate="show">

                  <div className="mb-6">
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Welcome back</h2>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                      Sign in to continue to your dashboard
                    </p>
                  </div>

                  {/* Global error */}
                  {error && (
                    <motion.div
                      className="flex items-start gap-2 p-3 mb-4 rounded-xl
                                 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm"
                      initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                    >
                      <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
                      <span className="text-red-700 dark:text-red-400">{error}</span>
                      <button onClick={clearError} className="ml-auto text-red-500 font-bold text-base leading-none">×</button>
                    </motion.div>
                  )}

                  <form onSubmit={handleSubmit} noValidate className="space-y-5">

                    {/* Email */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                        Email Address
                      </label>
                      <div className="relative">
                        <Mail size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                          type="email"
                          autoComplete="email"
                          placeholder="you@example.com"
                          value={email}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
                          onBlur={() => setTouched(t => ({ ...t, email: true }))}
                          className={`w-full pl-10 pr-4 py-2.5 rounded-xl border text-sm transition
                                      bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                                      focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500
                                      ${emailErr
                                        ? 'border-red-400 dark:border-red-600'
                                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                                      }`}
                        />
                      </div>
                      {emailErr && (
                        <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                          <AlertCircle size={12} />{emailErr}
                        </p>
                      )}
                    </div>

                    {/* Password */}
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                        Password
                      </label>
                      <div className="relative">
                        <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input
                          type={showPw ? 'text' : 'password'}
                          autoComplete="current-password"
                          placeholder="••••••••"
                          value={password}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setPassword(e.target.value)}
                          onBlur={() => setTouched(t => ({ ...t, password: true }))}
                          className={`w-full pl-10 pr-11 py-2.5 rounded-xl border text-sm transition
                                      bg-white dark:bg-gray-800 text-gray-900 dark:text-white
                                      focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500
                                      ${passwordErr
                                        ? 'border-red-400 dark:border-red-600'
                                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                                      }`}
                        />
                        <button
                          type="button"
                          onClick={() => setShowPw(v => !v)}
                          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                          tabIndex={-1}
                        >
                          {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                      {passwordErr && (
                        <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                          <AlertCircle size={12} />{passwordErr}
                        </p>
                      )}
                    </div>

                    {/* Remember + Forgot */}
                    <div className="flex items-center justify-between text-sm">
                      <label className="flex items-center gap-2 text-gray-600 dark:text-gray-400 cursor-pointer">
                        <input type="checkbox" className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500" />
                        Remember me
                      </label>
                      <Link to="/forgot-password"
                        className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-800 font-medium">
                        Forgot password?
                      </Link>
                    </div>

                    {/* Submit */}
                    <button
                      type="submit"
                      disabled={isLoading}
                      className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60
                                 text-white font-semibold text-sm flex items-center justify-center gap-2 transition"
                    >
                      {isLoading ? (
                        <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                      ) : (
                        <>Sign In <ChevronRight size={15} /></>
                      )}
                    </button>
                  </form>

                  {/* Divider */}
                  <div className="flex items-center gap-3 my-5">
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                    <span className="text-xs text-gray-400">or</span>
                    <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
                  </div>

                  {/* OAuth */}
                  <OAuthButtons
                    onSuccess={() => { showSuccessToast('Login successful!'); navigate('/dashboard') }}
                    onError={(msg) => showErrorToast(msg ?? 'OAuth login failed')}
                  />

                  {/* Register link */}
                  <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">
                      Create one free
                    </Link>
                  </p>

                </motion.div>
              )}
            </AnimatePresence>
          </div>

        </motion.div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <Footer />
    </div>
  )
}
