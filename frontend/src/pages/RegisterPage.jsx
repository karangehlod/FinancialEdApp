import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Lock, Mail, Eye, EyeOff, AlertCircle, CheckCircle, User } from 'lucide-react'
import FinEdLogo from '../assets/FinEdLogo.png'
import { useAuthStore } from '../store/authStore'
import { Input, Button, Alert } from '../components/UI'
import { Footer } from '../components/Footer'
import OAuthButtons from '../components/OAuthButtons'
import { showErrorToast, showSuccessToast } from '../utils/toast'
import { validateEmail } from '../utils/helpers'

export const RegisterPage = () => {
  const navigate = useNavigate()
  const { register, isLoading, error, clearError } = useAuthStore()
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    confirm_password: '',
  })
  const [formErrors, setFormErrors] = useState({})
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [focusedField, setFocusedField] = useState(null)
  const [touched, setTouched] = useState({})

  // Real-time validation for password strength
  const getPasswordStrength = (password) => {
    if (!password) return 0
    let strength = 0
    if (password.length >= 8) strength++
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++
    if (/\d/.test(password)) strength++
    if (/[!@#$%^&*]/.test(password)) strength++
    return strength
  }

  const passwordStrength = getPasswordStrength(formData.password)
  const strengthColor = {
    0: 'bg-gray-300',
    1: 'bg-red-400',
    2: 'bg-orange-400',
    3: 'bg-yellow-400',
    4: 'bg-green-400',
  }

  const validateForm = () => {
    const errors = {}
    if (!formData.name) errors.name = 'Name is required'
    if (!formData.email) errors.email = 'Email is required'
    else if (!validateEmail(formData.email)) errors.email = 'Invalid email format'
    if (!formData.password) errors.password = 'Password is required'
    else if (formData.password.length < 8) errors.password = 'Password must be at least 8 characters'
    if (!formData.confirm_password) errors.confirm_password = 'Please confirm your password'
    else if (formData.password !== formData.confirm_password)
      errors.confirm_password = 'Passwords do not match'
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
      await register({
        name: formData.name,
        email: formData.email,
        password: formData.password,
      })
      showSuccessToast('Registration successful! Please log in.')
      try {
        // Use hard redirect to avoid any router race conditions
        window.location.replace('/login')
      } catch (e) {
        navigate('/login')
      }
    } catch (err) {
      showErrorToast(error || 'Registration failed')
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
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-gray-900 dark:to-slate-900 flex flex-col relative overflow-hidden">
      <div className="flex-1 flex items-center justify-center p-4 relative">
      {/* Animated Background Blobs */}
      <motion.div
        className="absolute top-0 right-0 rounded-full blur-3xl opacity-20 pointer-events-none"
        style={{ width: 'var(--bg-blob-size)', height: 'var(--bg-blob-size)', backgroundColor: 'var(--bg-blob-primary, #bfdbfe)' }}
        animate={{ y: [0, 100, 0], x: [0, 50, 0] }}
        transition={{ duration: 15, repeat: Infinity }}
      />
      <motion.div
        className="absolute bottom-0 left-0 rounded-full blur-3xl opacity-20 pointer-events-none"
        style={{ width: 'var(--bg-blob-size)', height: 'var(--bg-blob-size)', backgroundColor: 'var(--bg-blob-secondary, #d8b4fe)' }}
        animate={{ y: [0, -100, 0], x: [0, -50, 0] }}
        transition={{ duration: 20, repeat: Infinity }}
      />

      {/* Main Content */}
      <motion.div className="relative z-10 w-full" style={{ maxWidth: 'var(--content-max-width)' }}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Header Section */}
        <motion.div className="mb-10" variants={itemVariants}>
          <motion.div
            className="flex flex-col sm:flex-row items-center gap-4 justify-center"
            initial={{ scale: 0, rotate: -20 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ delay: 0.2, type: 'spring', stiffness: 100 }}
          >
            <div
              className="flex-shrink-0 rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center"
              style={{
                width: 'var(--page-hero-icon-size)',
                height: 'var(--page-hero-icon-size)',
                boxShadow: '0 12px 36px rgba(2,6,23,0.12)',
              }}
            >
              <img src={FinEdLogo} alt="FinEd" style={{ width: '80%', height: '80%' }} className="object-contain" />
            </div>

            <div className="text-center sm:text-left">
              <motion.h1 className="font-bold text-gray-900 dark:text-gray-100 mb-0" style={{ fontSize: 'var(--font-xxl)' }} variants={itemVariants}>
                Create Account
              </motion.h1>
              <motion.p className="text-gray-600 dark:text-gray-400 mt-1" style={{ fontSize: 'var(--font-lg)' }} variants={itemVariants}>
                Join FinEd and start managing your finances
              </motion.p>
            </div>
          </motion.div>
        </motion.div>

        {/* Register Form Card */}
        <motion.form
          onSubmit={handleSubmit}
          className="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl dark:shadow-xl dark:shadow-black/20 ring-1 ring-transparent dark:ring-gray-700 border border-transparent dark:border-gray-700 backdrop-blur-sm space-y-5"
          style={{ padding: 'var(--spacing-md)' }}
          variants={itemVariants}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          {/* Error Alert */}
          <motion.div variants={itemVariants}>
            {error && (
              <motion.div
                className="flex items-start gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg shadow-sm"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-red-900 dark:text-red-300">Registration Failed</h3>
                  <p className="text-sm text-red-700 dark:text-red-400 mt-0.5">{error}</p>
                </div>
                <button
                  onClick={clearError}
                  className="text-red-600 hover:text-red-700 font-bold bg-red-50 dark:bg-transparent px-2 py-1 rounded hover:bg-red-100 dark:hover:bg-red-800/30 transition-colors"
                  type="button"
                >
                  ×
                </button>
              </motion.div>
            )}
          </motion.div>

          {/* Name Input */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-200 mb-2">
              Full Name
            </label>
            <motion.div
              className="relative shadow-sm rounded-lg"
              animate={{
                boxShadow:
                  focusedField === 'name'
                    ? '0 8px 30px rgba(79, 70, 229, 0.12)'
                    : '0 0 0 0px rgba(0,0,0,0)',
              }}
            >
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500">
                <User size={20} />
              </div>
              <input
                type="text"
                placeholder="John Doe"
                value={formData.name}
                onChange={(e) => {
                  setFormData({ ...formData, name: e.target.value })
                  setTouched({ ...touched, name: true })
                }}
                onFocus={() => setFocusedField('name')}
                onBlur={() => setFocusedField(null)}
                className={`w-full pl-10 pr-4 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ${
                  focusedField === 'name'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
                    : formErrors.name
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-700`}
              />
            </motion.div>
            {formErrors.name && (
              <motion.p
                className="text-sm text-red-600 mt-2 flex items-center gap-1"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={14} />
                {formErrors.name}
              </motion.p>
            )}
          </motion.div>

          {/* Email Input */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-200 mb-2">
              Email Address
            </label>
            <motion.div
              className="relative shadow-sm rounded-lg"
              animate={{
                boxShadow:
                  focusedField === 'email'
                    ? '0 8px 30px rgba(79, 70, 229, 0.12)'
                    : '0 0 0 0px rgba(0,0,0,0)',
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
                className={`w-full pl-10 pr-4 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ${
                  focusedField === 'email'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
                    : formErrors.email
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-700`}
              />
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
              className="relative shadow-sm rounded-lg"
              animate={{
                boxShadow:
                  focusedField === 'password'
                    ? '0 8px 30px rgba(79, 70, 229, 0.12)'
                    : '0 0 0 0px rgba(0,0,0,0)',
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
                className={`w-full pl-10 pr-12 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ${
                  focusedField === 'password'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
                    : formErrors.password
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-700`}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </motion.div>

            {/* Password Strength Indicator */}
            {formData.password && (
              <motion.div className="mt-2" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="flex gap-1 mb-1">
                  {[...Array(4)].map((_, i) => (
                    <div
                      key={i}
                      className={`h-1 flex-1 rounded-full transition-all ${
                        i < passwordStrength
                          ? strengthColor[passwordStrength]
                          : 'bg-gray-200'
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-gray-500">
                  {passwordStrength === 1 && 'Weak password'}
                  {passwordStrength === 2 && 'Fair password'}
                  {passwordStrength === 3 && 'Good password'}
                  {passwordStrength === 4 && '💪 Strong password'}
                </p>
              </motion.div>
            )}

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

          {/* Confirm Password Input */}
          <motion.div variants={itemVariants}>
            <label className="block text-sm font-semibold text-gray-900 dark:text-gray-200 mb-2">
              Confirm Password
            </label>
            <motion.div
              className="relative shadow-sm rounded-lg"
              animate={{
                boxShadow:
                  focusedField === 'confirm_password'
                    ? '0 8px 30px rgba(79, 70, 229, 0.12)'
                    : '0 0 0 0px rgba(0,0,0,0)',
              }}
            >
              <div className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 dark:text-gray-500">
                <Lock size={20} />
              </div>
              <input
                type={showConfirmPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.confirm_password}
                onChange={(e) => {
                  setFormData({ ...formData, confirm_password: e.target.value })
                  setTouched({ ...touched, confirm_password: true })
                }}
                onFocus={() => setFocusedField('confirm_password')}
                onBlur={() => setFocusedField(null)}
                className={`w-full pl-10 pr-12 py-3 border-2 rounded-lg transition-all duration-200 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 shadow-sm ${
                  focusedField === 'confirm_password'
                    ? 'border-indigo-500 bg-indigo-50 dark:bg-gray-600 ring-2 ring-indigo-200 dark:ring-indigo-800'
                    : formErrors.confirm_password
                      ? 'border-red-300 bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
                      : 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 hover:border-gray-300 dark:hover:border-gray-500'
                } focus:outline-none focus:ring-2 focus:ring-indigo-300 dark:focus:ring-indigo-700`}
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
              >
                {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </motion.div>

            {formData.confirm_password && formData.password === formData.confirm_password && !formErrors.confirm_password && (
              <motion.p
                className="text-sm text-green-600 mt-2 flex items-center gap-1"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <CheckCircle size={14} />
                Passwords match!
              </motion.p>
            )}

            {formErrors.confirm_password && (
              <motion.p
                className="text-sm text-red-600 mt-2 flex items-center gap-1"
                initial={{ opacity: 0, y: -5 }}
                animate={{ opacity: 1, y: 0 }}
              >
                <AlertCircle size={14} />
                {formErrors.confirm_password}
              </motion.p>
            )}
          </motion.div>

          {/* Submit Button */}
          <motion.button
            type="submit"
            disabled={isLoading}
            className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-gray-400 disabled:to-gray-500 text-white font-bold rounded-lg transition-all duration-200 shadow-lg hover:shadow-xl disabled:shadow-none flex items-center justify-center gap-2 mt-6"
            style={{ padding: 'var(--btn-padding)' }}
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
                Creating account...
              </>
            ) : (
              'Create Account'
            )}
          </motion.button>

          {/* Divider + OAuth */}
          <motion.div className="flex items-center gap-3" variants={itemVariants}>
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600"></div>
            <span className="text-sm text-gray-500 dark:text-gray-400">or</span>
            <div className="flex-1 h-px bg-gray-200 dark:bg-gray-600"></div>
          </motion.div>

          <motion.div variants={itemVariants}>
            <OAuthButtons
              redirectUri={`${window.location.origin}/auth/callback`}
              onSuccess={() => {
                showSuccessToast('Account created!')
                navigate('/dashboard')
              }}
              onError={(err) => showErrorToast(err.message || 'OAuth signup failed')}
            />
          </motion.div>

          {/* Sign In Link */}
          <motion.div className="text-center" variants={itemVariants}>
            <p className="text-gray-600 dark:text-gray-400">
              Already have an account?{' '}
              <Link
                to="/login"
                className="text-indigo-600 hover:text-indigo-700 font-bold transition-colors"
              >
                Sign in here
              </Link>
            </p>
          </motion.div>
        </motion.form>

        {/* Footer Info */}
        <motion.div
          className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400"
          variants={itemVariants}
        >
          <p>🔒 Your data is secure and encrypted</p>
        </motion.div>
      </motion.div>
      </div>{/* end flex-1 center */}
      <Footer />
    </div>
  )
}
