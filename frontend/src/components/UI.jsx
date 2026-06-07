import React from 'react'
import { motion } from 'framer-motion'

/**
 * Loading Spinner Component
 */
export const LoadingSpinner = ({ size = 'md' }) => {
  const sizeMap = {
    sm: 'var(--spinner-sm)',
    md: 'var(--spinner-md)',
    lg: 'var(--spinner-lg)',
  }

  return (
    <div className="flex justify-center items-center">
      <motion.div
        style={{ width: sizeMap[size], height: sizeMap[size], borderTopColor: 'var(--tw-ring-color, #2563eb)' }}
        className={`border-4 border-primary-200 dark:border-primary-800 rounded-full`} 
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
    </div>
  )
}

/**
 * Card Component
 */
export const Card = ({ children, className = '', ...props }) => (
  <motion.div
    className={`glass rounded-lg p-6 shadow-card hover:shadow-card-hover dark:shadow-none dark:hover:shadow-lg dark:hover:shadow-primary-900/20 bg-white dark:bg-gray-800 bg-opacity-100 dark:bg-opacity-100 text-gray-900 dark:text-gray-100 w-full max-w-none overflow-visible min-w-0 min-h-0 box-border ${className}`}
    initial={{ opacity: 0, y: 10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3 }}
    {...props}
  >
    {children}
  </motion.div>
)

/**
 * Button Component
 */
export const Button = ({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  isLoading = false,
  className = '',
  ...props
}) => {
  const variants = {
    primary:
      'bg-gradient-to-r from-primary-600 to-secondary-600 text-white hover:from-primary-700 hover:to-secondary-700',
    secondary:
      'bg-white dark:bg-gray-800 text-primary-600 dark:text-primary-400 border-2 border-primary-600 dark:border-primary-500 hover:bg-primary-50 dark:hover:bg-gray-700',
    danger: 'bg-red-500 text-white hover:bg-red-600',
    ghost: 'text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-gray-800',
    outline: 'bg-transparent border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800',
  }

  const sizeStyles = {
    sm: { padding: 'var(--btn-sm-py) var(--btn-sm-px)', fontSize: 'var(--btn-sm-font)' },
    md: { padding: 'var(--btn-md-py) var(--btn-md-px)', fontSize: 'var(--btn-md-font)' },
    lg: { padding: 'var(--btn-lg-py) var(--btn-lg-px)', fontSize: 'var(--btn-lg-font)' },
  }

  return (
    <motion.button
      className={`
        ${variants[variant] || variants.primary}
        rounded-lg font-semibold
        disabled:opacity-50 disabled:cursor-not-allowed
        flex items-center justify-center gap-2 w-auto
        ${className}
      `}
      style={{ boxSizing: 'border-box', ...sizeStyles[size] }}
      disabled={disabled || isLoading}
      whileHover={{ scale: disabled ? 1 : 1.05 }}
      whileTap={{ scale: disabled ? 1 : 0.98 }}
      {...props}
    >
      {isLoading ? <LoadingSpinner size="sm" /> : children}
    </motion.button>
  )
}

/**
 * Input Component
 */
export const Input = ({
  label,
  error,
  className = '',
  ...props
}) => (
  <div className="space-y-1 sm:space-y-2">
    {label && <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 break-words">{label}</label>}
    <motion.input
      className={`
        w-full rounded-lg border-2 border-gray-200 dark:border-gray-600 text-sm
        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
        placeholder-gray-400 dark:placeholder-gray-500
        focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none transition-colors
        ${error ? 'border-red-500 dark:border-red-400' : ''}
        ${className}
      `}
      style={{ boxSizing: 'border-box', padding: 'var(--input-py) var(--input-px)', fontSize: 'var(--input-font)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      {...props}
    />
    {error && <p className="text-red-500 dark:text-red-400 text-xs sm:text-sm break-words">{error}</p>}
  </div>
)

/**
 * Select Component
 */
export const Select = ({
  label,
  options,
  error,
  className = '',
  ...props
}) => (
  <div className="space-y-1 sm:space-y-2">
    {label && <label className="block text-xs sm:text-sm font-medium text-gray-700 dark:text-gray-300 break-words">{label}</label>}
    <motion.select
      className={`
        w-full rounded-lg border-2 border-gray-200 dark:border-gray-600 text-sm
        bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
        focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none transition-colors
        ${error ? 'border-red-500 dark:border-red-400' : ''}
        ${className}
      `}
      style={{ boxSizing: 'border-box', padding: 'var(--input-py) var(--input-px)', fontSize: 'var(--input-font)' }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      {...props}
    >
      <option value="">Select an option</option>
      {options?.map((opt) => (
        <option key={opt.value} value={opt.value} className="break-words">
          {opt.label}
        </option>
      ))}
    </motion.select>
    {error && <p className="text-red-500 dark:text-red-400 text-xs sm:text-sm break-words">{error}</p>}
  </div>
)

/**
 * Badge Component
 */
export const Badge = ({ children, variant = 'primary', className = '' }) => {
  const variants = {
    primary: 'bg-primary-100 dark:bg-primary-900/40 text-primary-800 dark:text-primary-300',
    secondary: 'bg-secondary-100 dark:bg-secondary-900/40 text-secondary-800 dark:text-secondary-300',
    success: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300',
    warning: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300',
    danger: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-300',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${variants[variant]} ${className}`}>{children}</span>
  )
}

/**
 * Modal Component
 */
export const Modal = ({ isOpen, onClose, title, children, className = '' }) => {
  if (!isOpen) return null

  return (
    <motion.div
      className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-3 sm:p-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      onClick={onClose}
    >
      <motion.div
        className={`bg-white dark:bg-gray-800 rounded-lg shadow-xl dark:shadow-2xl w-full max-w-none max-h-[90vh] overflow-y-auto box-border min-h-0 ${className}`}
        style={{ maxWidth: 'var(--modal-max-width)', padding: 'var(--modal-padding-y) var(--modal-padding-x)' }}
        initial={{ scale: 0.95, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.95, opacity: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 dark:border-gray-700 sticky top-0 bg-white dark:bg-gray-800 bg-opacity-100 dark:bg-opacity-100 backdrop-blur-sm" style={{ padding: '0.75rem 1rem' }}>
          <h2 className="text-lg sm:text-xl font-bold text-gray-800 dark:text-gray-100 truncate break-words">{title}</h2>
        </div>
        <div style={{ padding: 'var(--modal-padding-y) var(--modal-padding-x)' }} className="min-h-0">{children}</div>
      </motion.div>
    </motion.div>
  )
}

/**
 * Alert Component
 */
export const Alert = ({ type = 'info', title, message, onClose, className = '' }) => {
  const types = {
    info: 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border-blue-300 dark:border-blue-700',
    success: 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border-green-300 dark:border-green-700',
    warning: 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300 border-yellow-300 dark:border-yellow-700',
    error: 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border-red-300 dark:border-red-700',
  }

  return (
    <motion.div
      className={`border-l-4 p-4 rounded ${types[type]} ${className} min-w-0 break-words`}
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -10 }}
    >
      {title && <p className="font-bold break-words">{title}</p>}
      {message && <p className="text-sm break-words">{message}</p>}
      {onClose && (
        <button onClick={onClose} className="mt-2 text-sm font-semibold hover:underline">
          Dismiss
        </button>
      )}
    </motion.div>
  )
}

/**
 * Statistic Card Component
 */
export const StatCard = ({ icon: Icon, label, value, subtext, color = 'primary' }) => (
  <Card className={`border-l-4 border-${color}-600 w-full max-w-none`}>
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 min-h-0">
      <div className="flex-1 min-w-0">
        <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 font-medium break-words">{label}</p>
        <p className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 mt-2 break-words whitespace-normal">{value}</p>
        {subtext && <p className="text-gray-500 dark:text-gray-400 text-xs mt-1 break-words">{subtext}</p>}
      </div>
      {Icon && (
        <div className="rounded-lg flex-shrink-0" style={{ padding: 'var(--icon-md)', backgroundColor: 'var(--icon-bg, transparent)' }}>
          <Icon className={`w-[var(--icon-md)] h-[var(--icon-md)] text-${color}-600 dark:text-${color}-400`} />
        </div>
      )}
    </div>
  </Card>
)

/**
 * Empty State Component
 */
export const EmptyState = ({ icon: Icon, title, description, action, message }) => (
  <motion.div className="flex flex-col items-center justify-center py-8 sm:py-12 text-center px-4 min-w-0 break-words">
    {Icon && <Icon className="w-[var(--icon-lg)] h-[var(--icon-md)] text-gray-300 dark:text-gray-600 mb-3 sm:mb-4" />}
    <h3 className="text-lg sm:text-xl font-semibold text-gray-800 dark:text-gray-200 break-words whitespace-normal">{title}</h3>
    {description && <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mt-2 break-words">{description}</p>}
    {message && <p className="text-sm sm:text-base text-gray-600 dark:text-gray-400 mt-2 break-words">{message}</p>}
    {action && <div className="mt-4 sm:mt-6">{action}</div>}
  </motion.div>
)

/**
 * Progress Bar Component
 */
export const ProgressBar = ({ value, max = 100, color = 'primary', showLabel = true }) => {
  const percentage = (value / max) * 100

  // Color mapping for Tailwind classes
  const colorClasses = {
    primary: 'from-blue-500 to-blue-600',
    yellow: 'from-yellow-500 to-yellow-600',
    red: 'from-red-500 to-red-600',
    green: 'from-green-500 to-green-600',
  }

  const gradientClass = colorClasses[color] || colorClasses.primary

  return (
    <div className="w-full">
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden" style={{ height: 'var(--progress-height)' }}>
        <motion.div
          className={`h-full bg-gradient-to-r ${gradientClass}`}
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
      {showLabel && (
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 truncate">
          {value} / {max}
        </p>
      )}
    </div>
  )
}
