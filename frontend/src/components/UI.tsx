/**
 * Reusable UI primitives — fully typed, accessible, and responsive.
 * All components use Tailwind design tokens and follow WCAG 2.1 AA.
 */

import { type ReactNode, type ButtonHTMLAttributes, type InputHTMLAttributes, type SelectHTMLAttributes, forwardRef, memo, type ComponentType } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/utils/helpers'
import type { ButtonVariant, ButtonSize, BadgeVariant, IconSize } from '@/types'

// ── Loading Spinner ────────────────────────────────────────────────────

interface SpinnerProps {
  readonly size?: IconSize
}

export const LoadingSpinner = memo<SpinnerProps>(function LoadingSpinner({ size = 'md' }) {
  const sizeMap: Record<IconSize, string> = {
    sm: 'var(--spinner-sm, 1rem)',
    md: 'var(--spinner-md, 1.5rem)',
    lg: 'var(--spinner-lg, 2.5rem)',
  }

  return (
    <div className="flex items-center justify-center" role="status" aria-label="Loading">
      <motion.div
        style={{ width: sizeMap[size], height: sizeMap[size] }}
        className="border-4 border-primary-200 dark:border-primary-800 border-t-primary-600 rounded-full"
        animate={{ rotate: 360 }}
        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      />
      <span className="sr-only">Loading…</span>
    </div>
  )
})

// ── FluidIcon ──────────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- Lucide icons pass broader prop types
export type IconComponent = ComponentType<Record<string, any>>

interface FluidIconProps {
  readonly icon: IconComponent
  readonly size?: IconSize
  readonly className?: string
  readonly label?: string
}

export const FluidIcon = memo<FluidIconProps>(function FluidIcon({
  icon: Icon,
  size = 'md',
  className = '',
  label,
}) {
  const sizeStyle: Record<IconSize, React.CSSProperties> = {
    sm: { width: 'var(--icon-sm, 1rem)', height: 'var(--icon-sm, 1rem)' },
    md: { width: 'var(--icon-md, 1.5rem)', height: 'var(--icon-md, 1.5rem)' },
    lg: { width: 'var(--icon-lg, 2.25rem)', height: 'var(--icon-lg, 2.25rem)' },
  }

  // Always add an explicit icon-size class so CSS rules targeting svg.icon-sm / .icon-md / .icon-lg match
  const sizeClass = `icon-${size}`

  return (
    <span
      className={cn(sizeClass, className)}
      role={label ? 'img' : undefined}
      aria-label={label}
      aria-hidden={!label}
      style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', ...sizeStyle[size] }}
    >
      {/* Pass stroke and fill to the underlying svg and forward any className so defensive CSS selectors apply
          Use width/height 100% so the svg scales to the wrapper size. */}
      <Icon aria-hidden style={{ width: '100%', height: '100%' }} stroke="currentColor" fill="none" className={sizeClass} />
    </span>
  )
})

// ── Card ───────────────────────────────────────────────────────────────

interface CardProps {
  readonly children: ReactNode
  readonly className?: string
  readonly onClick?: () => void
}

export const Card = memo<CardProps>(function Card({ children, className, onClick }) {
  return (
    <motion.div
      className={cn(
        'glass rounded-lg shadow-card hover:shadow-card-hover dark:shadow-none',
        'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
        'w-full min-w-0 overflow-visible box-border',
        className,
      )}
      style={{ padding: 'var(--card-padding)' }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {children}
    </motion.div>
  )
})

// ── Button ─────────────────────────────────────────────────────────────

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant
  readonly size?: ButtonSize
  readonly isLoading?: boolean
  readonly children: ReactNode
}

const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-gradient-to-r from-primary-600 to-secondary-600 text-white hover:from-primary-700 hover:to-secondary-700',
  secondary: 'bg-white dark:bg-gray-800 text-primary-600 dark:text-primary-400 border-2 border-primary-600 dark:border-primary-500 hover:bg-primary-50 dark:hover:bg-gray-700',
  danger: 'bg-red-500 text-white hover:bg-red-600',
  ghost: 'text-primary-600 dark:text-primary-400 hover:bg-primary-50 dark:hover:bg-gray-800',
  outline: 'bg-transparent border-2 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800',
}

const SIZE_STYLES: Record<ButtonSize, { padding: string; fontSize: string }> = {
  sm: { padding: 'var(--btn-sm-py, 0.375rem) var(--btn-sm-px, 0.75rem)', fontSize: 'var(--btn-sm-font, 0.75rem)' },
  md: { padding: 'var(--btn-md-py, 0.5rem) var(--btn-md-px, 1rem)', fontSize: 'var(--btn-md-font, 0.875rem)' },
  lg: { padding: 'var(--btn-lg-py, 0.75rem) var(--btn-lg-px, 1.5rem)', fontSize: 'var(--btn-lg-font, 1rem)' },
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', isLoading = false, disabled, className, children, type = 'button', onClick, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        VARIANT_CLASSES[variant],
        'rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed',
        'flex items-center justify-center gap-2 transition-all duration-200',
        'hover:scale-[1.02] active:scale-[0.98]',
        className,
      )}
      style={SIZE_STYLES[size]}
      // also allow token class for fluid sizing
      data-btn-size={size}
      disabled={disabled || isLoading}
      onClick={onClick}
      {...rest}
    >
      {isLoading ? <LoadingSpinner size="sm" /> : children}
    </button>
  )
})

// ── Input ──────────────────────────────────────────────────────────────

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  readonly label?: string
  readonly error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { label, error, className, id, ...props },
  ref,
) {
  const inputId = id ?? `input-${label?.toLowerCase().replace(/\s/g, '-') ?? 'field'}`

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={inputId} className="block text-sm-fluid font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={cn(
          'w-full rounded-lg border-2 border-gray-200 dark:border-gray-600 text-sm-fluid',
          'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
          'placeholder-gray-400 dark:placeholder-gray-500',
          'focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20',
          'transition-colors',
          error && 'border-red-500 dark:border-red-400',
          className,
        )}
        style={{ padding: 'var(--input-py, 0.625rem) var(--input-px, 0.75rem)', fontSize: 'var(--input-font, 0.875rem)' }}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={error ? `${inputId}-error` : undefined}
        {...props}
      />
      {error && (
        <p id={`${inputId}-error`} className="text-red-500 dark:text-red-400 text-sm-fluid" role="alert">
          {error}
        </p>
      )}
    </div>
  )
})

// ── Select ─────────────────────────────────────────────────────────────

interface SelectOption {
  readonly value: string
  readonly label: string
}

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  readonly label?: string
  readonly options: readonly SelectOption[]
  readonly error?: string
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, options, error, className, id, ...props },
  ref,
) {
  const selectId = id ?? `select-${label?.toLowerCase().replace(/\s/g, '-') ?? 'field'}`

  return (
    <div className="space-y-1.5">
      {label && (
        <label htmlFor={selectId} className="block text-sm-fluid font-medium text-gray-700 dark:text-gray-300">
          {label}
        </label>
      )}
      <select
        ref={ref}
        id={selectId}
        className={cn(
          'w-full rounded-lg border-2 border-gray-200 dark:border-gray-600 text-sm-fluid',
          'bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100',
          'focus:border-primary-500 dark:focus:border-primary-400 focus:outline-none focus:ring-2 focus:ring-primary-500/20',
          'transition-colors',
          error && 'border-red-500 dark:border-red-400',
          className,
        )}
        style={{ padding: 'var(--input-py, 0.625rem) var(--input-px, 0.75rem)', fontSize: 'var(--input-font, 0.875rem)' }}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      >
        <option value="">Select an option</option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="text-red-500 dark:text-red-400 text-sm-fluid" role="alert">
          {error}
        </p>
      )}
    </div>
  )
})

// ── Badge ──────────────────────────────────────────────────────────────

interface BadgeProps {
  readonly children: ReactNode
  readonly variant?: BadgeVariant
  readonly className?: string
}

const BADGE_VARIANTS: Record<BadgeVariant, string> = {
  primary: 'bg-primary-100 dark:bg-primary-900/40 text-primary-800 dark:text-primary-300',
  secondary: 'bg-secondary-100 dark:bg-secondary-900/40 text-secondary-800 dark:text-secondary-300',
  success: 'bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-300',
  warning: 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-800 dark:text-yellow-300',
  danger: 'bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-300',
}

export const Badge = memo<BadgeProps>(function Badge({ children, variant = 'primary', className }) {
  return (
    <span className={cn('px-3 py-1 rounded-full text-sm-fluid font-medium', BADGE_VARIANTS[variant], className)}>
      {children}
    </span>
  )
})

// ── Modal ──────────────────────────────────────────────────────────────

interface ModalProps {
  readonly isOpen: boolean
  readonly onClose: () => void
  readonly title: string
  readonly children: ReactNode
  readonly className?: string
}

export const Modal = memo<ModalProps>(function Modal({ isOpen, onClose, title, children, className }) {
  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 bg-black/50 dark:bg-black/70 flex items-center justify-center z-50 p-4"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        <motion.div
          className={cn(
            'bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-h-[90vh] overflow-y-auto',
            className,
          )}
          style={{ maxWidth: 'var(--modal-max-width, 32rem)', padding: 'var(--modal-padding-y, 1.5rem) var(--modal-padding-x, 1.5rem)' }}
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="border-b border-gray-200 dark:border-gray-700 pb-3 mb-4">
            <h2 id="modal-title" className="text-lg font-bold text-gray-800 dark:text-gray-100">
              {title}
            </h2>
          </div>
          <div>{children}</div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
})

// ── Alert ──────────────────────────────────────────────────────────────

interface AlertProps {
  readonly children: ReactNode
  readonly variant?: 'info' | 'success' | 'warning' | 'error'
  readonly className?: string
}

const ALERT_VARIANTS: Record<NonNullable<AlertProps['variant']>, string> = {
  info: 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-300',
  success: 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800 text-green-800 dark:text-green-300',
  warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800 text-yellow-800 dark:text-yellow-300',
  error: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-800 dark:text-red-300',
}

export const Alert = memo<AlertProps>(function Alert({ children, variant = 'info', className }) {
  return (
    <div
      className={cn('p-4 rounded-lg border', ALERT_VARIANTS[variant], className)}
      role="alert"
    >
      {children}
    </div>
  )
})

// ── StatCard ───────────────────────────────────────────────────────────

interface StatCardProps {
  readonly title: string
  readonly value: string | number
  readonly icon?: IconComponent
  readonly trend?: { value: number; positive: boolean }
  readonly className?: string
}

export const StatCard = memo<StatCardProps>(function StatCard({ title, value, icon: Icon, trend, className }) {
  return (
    <Card className={className}>
      <div className="flex items-center justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm-fluid font-medium text-gray-500 dark:text-gray-400 truncate">{title}</p>
          <p className="text-value text-gray-900 dark:text-gray-100 mt-1">{value}</p>
          {trend && (
            <p
              className={cn(
                'text-sm mt-1 font-medium',
                trend.positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400',
              )}
            >
              {trend.positive ? '↑' : '↓'} {Math.abs(trend.value)}%
            </p>
          )}
        </div>
        {Icon && (
          <div className="flex-shrink-0 ml-4">
            <FluidIcon icon={Icon} size="lg" className="text-primary-500" />
          </div>
        )}
      </div>
    </Card>
  )
})

// ── EmptyState ─────────────────────────────────────────────────────────

interface EmptyStateProps {
  readonly icon?: IconComponent
  readonly title: string
  readonly description?: string
  readonly action?: ReactNode
}

export const EmptyState = memo<EmptyStateProps>(function EmptyState({ icon: Icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center" role="status">
      {Icon && (
        <div className="mb-4 p-3 bg-gray-100 dark:bg-gray-800 rounded-full">
          <FluidIcon icon={Icon} size="lg" className="text-gray-400 dark:text-gray-500" />
        </div>
      )}
      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h3>
      {description && <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mt-2 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
})

// ── ProgressBar ────────────────────────────────────────────────────────

interface ProgressBarProps {
  readonly value: number
  readonly max?: number
  readonly className?: string
  readonly color?: string
}

export const ProgressBar = memo<ProgressBarProps>(function ProgressBar({ value, max = 100, className, color }) {
  // Support both percentage-style usage (value in 0-100 with max=100) and absolute-amount usage
  // (value is amount spent and max is allocation). Also accept both Tailwind bg-* classes and
  // simple color tokens like 'primary', 'red', 'yellow'.
  const colorMap: Record<string, string> = {
    primary: 'bg-primary-600',
    secondary: 'bg-secondary-600',
    red: 'bg-red-500',
    yellow: 'bg-yellow-400',
    green: 'bg-green-500',
    blue: 'bg-blue-500',
  }

  const resolvedColorClass = color
    ? color.includes('bg-')
      ? color
      : colorMap[color] ?? `bg-${color}`
    : 'bg-primary-600'

  // Normalize numeric inputs and compute percentage safely
  const safeValue = Number.isFinite(Number(value)) ? Number(value) : 0
  const safeMax = Number.isFinite(Number(max)) ? Number(max) : 0

  let pct: number
  if (safeMax > 0) {
    pct = (safeValue / safeMax) * 100
  } else {
    // If max is 0 or invalid, treat incoming value as a percentage already
    pct = safeValue
  }

  // Guard against NaN and clamp
  if (!Number.isFinite(pct) || isNaN(pct)) pct = 0
  pct = Math.min(100, Math.max(0, pct))

  return (
    <div
      className={cn('w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden', className)}
      style={{ height: 'var(--progress-height, 0.5rem)' }}
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <motion.div
        className={cn('h-full rounded-full', resolvedColorClass)}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.5, ease: 'easeOut' }}
      />
    </div>
  )
})
