import React, { useState, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Lock, Mail, Eye, EyeOff, AlertCircle, User, ChevronRight,
  TrendingUp, PiggyBank, Target, BarChart2, Bell, MessageSquare,
  Shield, Zap, FileDown, RefreshCw,
} from 'lucide-react'

import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '@/store/authStore'
import OAuthButtons from '@/components/OAuthButtons'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import { validateEmail } from '@/utils/helpers'
import { Footer } from '@/components/Footer'

// ── Types ──────────────────────────────────────────────────────────────────

interface RegisterForm {
  first_name: string
  last_name:  string
  email:      string
  password:   string
  confirm:    string
}

type FormErrors = Partial<Record<keyof RegisterForm, string>>
type PasswordStrength = 0 | 1 | 2 | 3 | 4

// ── Helpers ────────────────────────────────────────────────────────────────

const getStrength = (pw: string): PasswordStrength => {
  if (!pw) return 0
  let s = 0
  if (pw.length >= 8)                        s++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) s++
  if (/\d/.test(pw))                         s++
  if (/[!@#$%^&*]/.test(pw))                s++
  return s as PasswordStrength
}

const strengthLabels: Record<PasswordStrength, { label: string; color: string }> = {
  0: { label: '',        color: 'bg-gray-200 dark:bg-gray-700' },
  1: { label: 'Weak',   color: 'bg-red-400' },
  2: { label: 'Fair',   color: 'bg-orange-400' },
  3: { label: 'Good',   color: 'bg-yellow-400' },
  4: { label: 'Strong', color: 'bg-emerald-500' },
}

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

// ── Component ──────────────────────────────────────────────────────────────

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()

  const [form, setForm]     = useState<RegisterForm>({
    first_name: '', last_name: '', email: '', password: '', confirm: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [showPw, setShowPw] = useState(false)
  const [showCf, setShowCf] = useState(false)

  const strength = getStrength(form.password)
  const sInfo    = strengthLabels[strength]

  const setField = useCallback(
    (field: keyof RegisterForm) =>
      (e: ChangeEvent<HTMLInputElement>) => {
        setForm(p => ({ ...p, [field]: e.target.value }))
        setErrors(p => ({ ...p, [field]: '' }))
      },
    [],
  )

  const validate = useCallback((): FormErrors => {
    const errs: FormErrors = {}
    if (!form.first_name.trim()) errs.first_name = 'First name is required'
    if (!form.last_name.trim())  errs.last_name  = 'Last name is required'
    if (!form.email)             errs.email      = 'Email is required'
    else if (!validateEmail(form.email)) errs.email = 'Invalid email format'
    if (!form.password)          errs.password   = 'Password is required'
    else if (form.password.length < 8)  errs.password = 'Minimum 8 characters'
    if (form.confirm !== form.password) errs.confirm = 'Passwords do not match'
    return errs
  }, [form])

  const handleSubmit = useCallback(async (e: FormEvent) => {
    e.preventDefault()
    clearError()
    const errs = validate()
    if (Object.keys(errs).length > 0) { setErrors(errs); return }
    try {
      await register({
        first_name: form.first_name.trim(),
        last_name:  form.last_name.trim(),
        email:      form.email,
        password:   form.password,
      })
      showSuccessToast('Account created! Please sign in.')
      navigate('/login')
    } catch {
      showErrorToast(error ?? 'Registration failed. Please try again.')
    }
  }, [form, validate, register, error, clearError, navigate])

  const inp = (field: keyof RegisterForm) => `
    w-full pl-10 pr-4 py-2.5 rounded-xl border text-sm transition
    bg-white dark:bg-gray-800 text-gray-900 dark:text-white
    focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:border-emerald-500
    ${errors[field]
      ? 'border-red-400 dark:border-red-600'
      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}
  `

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
                          bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-700
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
                <p className="text-emerald-200 text-sm leading-tight">Master Your Financial Future</p>
              </div>
            </div>

            {/* Headline */}
            <div className="mb-6">
              <h2 className="text-2xl xl:text-3xl font-extrabold leading-snug">
                Everything you need to manage your money — in one place.
              </h2>
              <p className="mt-3 text-emerald-100 text-sm leading-relaxed">
                Track expenses, plan budgets, hit savings goals, and get AI-powered insights.
                All your financial data, private and secure.
              </p>
            </div>

            {/* Features — real capabilities only */}
            <ul className="space-y-2.5 flex-1">
              {FEATURES.map(({ icon: Icon, label }) => (
                <li key={label} className="flex items-center gap-3 text-sm">
                  <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-white/15 flex items-center justify-center">
                    <Icon size={14} />
                  </span>
                  <span className="text-emerald-50">{label}</span>
                </li>
              ))}
            </ul>

            <p className="mt-8 text-emerald-300 text-xs">
              © {new Date().getFullYear()} FinancialEdApp · Built by Karan Gehlod
            </p>
          </div>

          {/* ── Right panel — registration form ────────────────────────── */}
          <div className="flex-1 bg-white dark:bg-gray-900 flex flex-col justify-center
                          px-6 py-8 sm:px-10 xl:px-12">

            <div className="mb-6">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Create your account</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Free to use · No credit card required
              </p>
            </div>

            {/* Global error */}
            {error && (
              <motion.div
                className="flex items-start gap-2 p-3 mb-5 rounded-xl
                           bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm"
                initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={15} className="text-red-500 mt-0.5 flex-shrink-0" />
                <span className="text-red-700 dark:text-red-400 flex-1">{error}</span>
                <button onClick={clearError} className="ml-auto text-red-500 font-bold text-base leading-none">×</button>
              </motion.div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-4">

              {/* Name row */}
              <div className="grid grid-cols-2 gap-3">
                {(['first_name', 'last_name'] as const).map((field) => (
                  <div key={field}>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                      {field === 'first_name' ? 'First name' : 'Last name'}
                    </label>
                    <div className="relative">
                      <User size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                      <input
                        type="text"
                        autoComplete={field === 'first_name' ? 'given-name' : 'family-name'}
                        placeholder={field === 'first_name' ? 'First' : 'Last'}
                        value={form[field]}
                        onChange={setField(field)}
                        className={inp(field)}
                      />
                    </div>
                    {errors[field] && (
                      <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                        <AlertCircle size={11} />{errors[field]}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Email Address
                </label>
                <div className="relative">
                  <Mail size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    value={form.email}
                    onChange={setField('email')}
                    className={inp('email')}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle size={11} />{errors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type={showPw ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Min 8 characters"
                    value={form.password}
                    onChange={setField('password')}
                    className={`${inp('password')} pr-11`}
                  />
                  <button type="button" tabIndex={-1} onClick={() => setShowPw(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {form.password && (
                  <div className="mt-2 space-y-1">
                    <div className="flex gap-1">
                      {([1, 2, 3, 4] as const).map(n => (
                        <div key={n}
                          className={`h-1 flex-1 rounded-full transition-all duration-300
                                      ${n <= strength ? sInfo.color : 'bg-gray-200 dark:bg-gray-700'}`} />
                      ))}
                    </div>
                    {sInfo.label && (
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        Strength: <span className="font-medium">{sInfo.label}</span>
                      </p>
                    )}
                  </div>
                )}
                {errors.password && (
                  <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle size={11} />{errors.password}
                  </p>
                )}
              </div>

              {/* Confirm password */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type={showCf ? 'text' : 'password'}
                    autoComplete="new-password"
                    placeholder="Re-enter your password"
                    value={form.confirm}
                    onChange={setField('confirm')}
                    className={`${inp('confirm')} pr-11`}
                  />
                  <button type="button" tabIndex={-1} onClick={() => setShowCf(v => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
                    {showCf ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {errors.confirm && (
                  <p className="mt-1 text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle size={11} />{errors.confirm}
                  </p>
                )}
              </div>

              {/* Terms */}
              <p className="text-xs text-gray-500 dark:text-gray-400">
                By creating an account you agree to our{' '}
                <Link to="/terms" className="text-emerald-600 dark:text-emerald-400 hover:underline">Terms</Link>
                {' '}and{' '}
                <Link to="/privacy" className="text-emerald-600 dark:text-emerald-400 hover:underline">Privacy Policy</Link>.
              </p>

              {/* Submit */}
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-60
                           text-white font-semibold text-sm flex items-center justify-center gap-2 transition"
              >
                {isLoading ? (
                  <span className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                ) : (
                  <>Create Account <ChevronRight size={15} /></>
                )}
              </button>
            </form>

            {/* Divider + OAuth */}
            <div className="flex items-center gap-3 my-4">
              <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
              <span className="text-xs text-gray-400">or sign up with</span>
              <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
            </div>

            <OAuthButtons
              onSuccess={() => { showSuccessToast('Signed up!'); navigate('/dashboard') }}
              onError={(msg) => showErrorToast(msg ?? 'OAuth signup failed')}
            />

            <p className="mt-5 text-center text-sm text-gray-500 dark:text-gray-400">
              Already have an account?{' '}
              <Link to="/login" className="text-emerald-600 dark:text-emerald-400 font-semibold hover:underline">
                Sign in
              </Link>
            </p>
          </div>

        </motion.div>
      </main>

      {/* ── Footer ──────────────────────────────────────────────────────── */}
      <Footer />
    </div>
  )
}
