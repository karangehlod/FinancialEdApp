/**
 * RegisterPage — matching two-column layout to LoginPage.
 * Left: brand panel (lg+). Right: registration form.
 * Pure Tailwind — no custom CSS classes.
 */

import React, { useState, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Lock, Mail, Eye, EyeOff, AlertCircle, User, ChevronRight,
  TrendingUp, PiggyBank, Target, BarChart2,
} from 'lucide-react'

import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '@/store/authStore'
import OAuthButtons from '@/components/OAuthButtons'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import { validateEmail } from '@/utils/helpers'

// ── Types ──────────────────────────────────────────────────────────────────

interface RegisterForm {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm: string
}

type FormErrors = Partial<Record<keyof RegisterForm, string>>

type PasswordStrength = 0 | 1 | 2 | 3 | 4

// ── Helpers ────────────────────────────────────────────────────────────────

const getStrength = (pw: string): PasswordStrength => {
  if (!pw) return 0
  let s = 0
  if (pw.length >= 8)                              s++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw))       s++
  if (/\d/.test(pw))                               s++
  if (/[!@#$%^&*]/.test(pw))                       s++
  return s as PasswordStrength
}

const strengthLabels: Record<PasswordStrength, { label: string; color: string }> = {
  0: { label: '',        color: 'bg-gray-200 dark:bg-gray-700' },
  1: { label: 'Weak',   color: 'bg-red-400' },
  2: { label: 'Fair',   color: 'bg-orange-400' },
  3: { label: 'Good',   color: 'bg-yellow-400' },
  4: { label: 'Strong', color: 'bg-emerald-500' },
}

const STATS = [
  { icon: TrendingUp, value: '50K+',  label: 'Users' },
  { icon: PiggyBank,  value: '₹10Cr+', label: 'Tracked' },
  { icon: Target,     value: '95%',   label: 'Goal Hit Rate' },
  { icon: BarChart2,  value: '4.9★',  label: 'Rating' },
]

// ── Component ──────────────────────────────────────────────────────────────

export const RegisterPage: React.FC = () => {
  const navigate  = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()

  const [form, setForm]       = useState<RegisterForm>({
    first_name: '', last_name: '', email: '', password: '', confirm: '',
  })
  const [errors, setErrors]   = useState<FormErrors>({})
  const [showPw, setShowPw]   = useState(false)
  const [showCf, setShowCf]   = useState(false)

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
    else if (form.password.length < 8) errs.password = 'Minimum 8 characters'
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

  // ── Input class builder ────────────────────────────────────────────────

  const inp = (field: keyof RegisterForm) => `
    w-full pl-10 pr-4 py-2.5 rounded-xl border text-sm transition
    bg-white dark:bg-gray-800 text-gray-900 dark:text-white
    focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500
    ${errors[field]
      ? 'border-red-400 dark:border-red-600'
      : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}
  `

  // ── Render ─────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen flex flex-col lg:flex-row bg-gray-50 dark:bg-gray-950">

      {/* ── Left panel (lg+) ──────────────────────────────────────────── */}
      <div className="hidden lg:flex lg:w-[44%] xl:w-2/5 flex-col justify-between
                      bg-gradient-to-br from-emerald-600 via-teal-600 to-cyan-700
                      p-10 xl:p-14 text-white flex-shrink-0">

        {/* Brand */}
        <div className="flex items-center gap-3">
          <img src={FinEdLogo} alt="FinEd" className="w-10 h-10 rounded-xl object-contain" />
          <div>
            <p className="font-bold text-lg leading-tight">FinEd</p>
            <p className="text-emerald-200 text-sm leading-tight">Master Your Financial Future</p>
          </div>
        </div>

        {/* Hero copy */}
        <div className="space-y-8">
          <div>
            <h2 className="text-3xl xl:text-4xl font-extrabold leading-tight">
              Your financial journey<br />starts here. Free.
            </h2>
            <p className="mt-3 text-emerald-100 text-base leading-relaxed max-w-xs">
              Join thousands of users who have already transformed their finances with FinEd.
            </p>
          </div>

          {/* Stats grid */}
          <div className="grid grid-cols-2 gap-4">
            {STATS.map(({ icon: Icon, value, label }) => (
              <div key={label}
                className="bg-white/10 rounded-2xl p-4 flex flex-col gap-1 backdrop-blur-sm">
                <Icon size={20} className="text-emerald-200" />
                <p className="text-2xl font-extrabold">{value}</p>
                <p className="text-xs text-emerald-200">{label}</p>
              </div>
            ))}
          </div>

          {/* Testimonial */}
          <blockquote className="border-l-2 border-emerald-300 pl-4 italic text-sm text-emerald-100">
            "FinEd helped me save ₹2 lakh in under 6 months by showing me exactly where my money was going."
            <footer className="mt-1 not-italic text-emerald-300 text-xs">— Priya, Bangalore</footer>
          </blockquote>
        </div>

        <p className="text-emerald-300 text-xs">
          © {new Date().getFullYear()} FinancialEdApp. Your data stays private.
        </p>
      </div>

      {/* ── Right panel — form ─────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center
                      px-5 py-10 sm:px-8 lg:px-12 xl:px-16">

        {/* Mobile brand */}
        <div className="lg:hidden flex flex-col items-center gap-2 mb-8">
          <img src={FinEdLogo} alt="FinEd" className="w-14 h-14 rounded-2xl object-contain" />
          <h1 className="text-2xl font-extrabold text-gray-900 dark:text-white">FinEd</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Master Your Financial Future</p>
        </div>

        {/* Card */}
        <motion.div
          className="w-full max-w-md bg-white dark:bg-gray-900 rounded-2xl shadow-xl
                     border border-gray-100 dark:border-gray-800 p-8 sm:p-10"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="mb-7">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">Create your account</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              Free forever. No credit card required.
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
                      placeholder={field === 'first_name' ? 'Karan' : 'Gehlod'}
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
              {/* Strength bar */}
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
              <Link to="/terms" className="text-indigo-600 dark:text-indigo-400 hover:underline">Terms</Link>
              {' '}and{' '}
              <Link to="/privacy" className="text-indigo-600 dark:text-indigo-400 hover:underline">Privacy Policy</Link>.
            </p>

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
                <>Create Free Account <ChevronRight size={15} /></>
              )}
            </button>
          </form>

          {/* Divider + OAuth */}
          <div className="flex items-center gap-3 my-5">
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
            <span className="text-xs text-gray-400">or sign up with</span>
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-700" />
          </div>

          <OAuthButtons
            onSuccess={() => { showSuccessToast('Signed up!'); navigate('/dashboard') }}
            onError={(msg) => showErrorToast(msg ?? 'OAuth signup failed')}
          />

          <p className="mt-6 text-center text-sm text-gray-500 dark:text-gray-400">
            Already have an account?{' '}
            <Link to="/login" className="text-indigo-600 dark:text-indigo-400 font-semibold hover:underline">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  )
}
