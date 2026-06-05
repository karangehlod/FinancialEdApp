/**
 * Layout components — Sidebar, Header, Layout shell, and PageContainer.
 * Fully typed, memoized, responsive (320 px → 1920 px+), accessible.
 */

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  memo,
  isValidElement,
  type ReactNode,
} from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Home,
  Wallet,
  PieChart,
  Target,
  Zap,
  LogOut,
  Menu,
  X,
  Bell,
  User,
  BarChart3,
  Settings,
  MessageCircle,
  Sun,
  Moon,
  Shield,
} from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useNotificationStore } from '@/store/index'
import { useThemeStore } from '@/store/themeStore'
import { getInitials } from '@/utils/helpers'
import { Button, FluidIcon, type IconComponent } from './UI'
import { env } from '@/config/env'
import FinEdLogo from '@/assets/FinEdLogo.png'

// ── Types ──────────────────────────────────────────────────────────────

interface NavItem {
  readonly label: string
  readonly icon: IconComponent
  readonly path: string
}

interface SidebarProps {
  readonly isOpen: boolean
  readonly onClose: () => void
}

interface HeaderProps {
  readonly onMenuClick: () => void
  readonly onDesktopToggle: () => void
  readonly sidebarVisible: boolean
}

interface LayoutProps {
  readonly children: ReactNode
}

interface PageContainerProps {
  readonly title: string
  readonly subtitle?: string
  readonly action?: ReactNode
  readonly children: ReactNode
  readonly icon?: IconComponent | ReactNode | null
  readonly showLogo?: boolean
}

// ── Helpers ─────────────────────────────────────────────────────────────

function isAdminUser(email: string | null | undefined): boolean {
  if (!email) return false
  return env.adminEmails.includes(email.toLowerCase())
}

function buildNavItems(isAdmin: boolean): readonly NavItem[] {
  const base: NavItem[] = [
    { label: 'Dashboard', icon: Home, path: '/dashboard' },
    { label: 'Expenses', icon: Wallet, path: '/expenses' },
    { label: 'Budgets', icon: PieChart, path: '/budgets' },
    { label: 'Loans', icon: Zap, path: '/loans' },
    { label: 'Goals', icon: Target, path: '/goals' },
    { label: 'Reports', icon: BarChart3, path: '/reports' },
    { label: 'Chat', icon: MessageCircle, path: '/chat' },
    { label: 'Settings', icon: Settings, path: '/settings' },
  ]
  if (isAdmin) {
    base.push({ label: 'Admin', icon: Shield, path: '/admin' })
  }
  return base
}

// ── Sidebar ─────────────────────────────────────────────────────────────

export const Sidebar = memo<SidebarProps>(function Sidebar({ isOpen, onClose }) {
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)
  const user = useAuthStore((s) => s.user)
  const navItems = buildNavItems(isAdminUser(user?.email))

  const handleNavigation = useCallback(
    (path: string): void => {
      navigate(path)
      onClose()
    },
    [navigate, onClose],
  )

  const handleLogout = useCallback((): void => {
    logout()
    navigate('/login')
  }, [logout, navigate])

  return (
    <>
      {/* Mobile/Tablet Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-0 bg-black/50 lg:hidden z-40"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-56 sm:w-64 bg-gradient-to-b from-primary-900 to-primary-800
          text-white shadow-xl
          transform transition-transform duration-300 ease-in-out lg:translate-x-0
          flex flex-col h-full overflow-hidden
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        aria-label="Main navigation"
      >
        {/* Header */}
        <div className="border-b border-primary-700 flex-shrink-0">
          <div className="flex items-center justify-between px-4">
            <div
              className="sidebar-brand flex items-center justify-start w-full"
              style={{ minHeight: 'var(--sidebar-brand-height, 3.5rem)' }}
            >
              <img
                src={FinEdLogo}
                alt="FinEd"
                className="object-contain rounded sidebar-logo"
              />
              <div className="ml-2">
                <h1
                  className="font-bold gradient-text"
                  style={{ fontSize: 'var(--sidebar-title-size, 1.125rem)', lineHeight: 1 }}
                >
                  FinEd
                </h1>
                <p
                  className="text-primary-200 hidden sm:block"
                  style={{ fontSize: 'var(--sidebar-subtitle-size, 0.75rem)', margin: 0 }}
                >
                  Master Your Money
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="lg:hidden p-1 hover:bg-primary-700 rounded-lg transition-colors"
              aria-label="Close navigation menu"
            >
              <X className="w-5 h-5" aria-hidden="true" />
            </button>
          </div>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-1" aria-label="Sidebar navigation">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = location.pathname === item.path

            return (
              <button
                key={item.path}
                type="button"
                onClick={() => handleNavigation(item.path)}
                className={`
                  w-full flex items-center gap-3 px-4 py-2.5 rounded-lg
                  transition-all duration-200 text-left text-sm-fluid
                  ${
                    active
                      ? 'bg-white/20 text-white font-semibold'
                      : 'text-primary-200 hover:text-white hover:bg-white/10'
                  }
                `}
                aria-current={active ? 'page' : undefined}
              >
                <FluidIcon icon={Icon} size="md" className="flex-shrink-0 text-current" />
                <span className="flex-1 min-w-0 truncate">{item.label}</span>
              </button>
            )
          })}
        </nav>

        {/* Logout */}
        <div className="p-4 sm:p-6 border-t border-primary-700 flex-shrink-0">
          <Button
            onClick={handleLogout}
            variant="secondary"
            className="w-full text-primary-600 border-primary-200 hover:bg-primary-50"
          >
            <FluidIcon icon={LogOut} size="sm" className="mr-2" />
            <span>Logout</span>
          </Button>
          <p className="mt-4 text-center text-sm-fluid text-primary-400">
            Built by{' '}
            <span className="font-semibold text-primary-200">Karan Gehlod</span>
            <br />
            <a
              href="mailto:support+theprodsde@gmail.com"
              className="hover:text-white transition-colors"
            >
              support+theprodsde@gmail.com
            </a>
          </p>
        </div>
      </aside>
    </>
  )
})

// ── Header ──────────────────────────────────────────────────────────────

export const Header = memo<HeaderProps>(function Header({
  onMenuClick,
  onDesktopToggle,
  sidebarVisible,
}) {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const notifications = useNotificationStore((s) => s.notifications)
  const markNotificationAsRead = useNotificationStore((s) => s.markNotificationAsRead)
  const { toggleTheme, theme } = useThemeStore()
  const isDark = theme === 'dark'
  const unreadCount = notifications?.filter((n) => !n.read).length ?? 0

  const navigate = useNavigate()
  const [profileOpen, setProfileOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const profileRef = useRef<HTMLDivElement>(null)
  const notificationsRef = useRef<HTMLDivElement>(null)

  // Close dropdowns on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent): void => {
      const target = e.target as Node
      if (profileRef.current && !profileRef.current.contains(target)) {
        setProfileOpen(false)
      }
      if (notificationsRef.current && !notificationsRef.current.contains(target)) {
        setNotificationsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = useCallback((): void => {
    logout()
  }, [logout])

  const displayName =
    user?.name ??
    ([user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'User')

  return (
    <header className="app-header bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30 w-full">
      <div className="app-header-inner flex items-center justify-between px-3 sm:px-4 py-2">
        {/* Mobile Menu Button */}
        <button
          type="button"
          onClick={onMenuClick}
          className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          aria-label="Toggle navigation menu"
        >
          <Menu className="w-5 h-5" aria-hidden="true" />
        </button>

        {/* Desktop Sidebar Toggle */}
        <button
          type="button"
          onClick={onDesktopToggle}
          className="hidden lg:inline-flex p-2 ml-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          aria-label={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
        >
          {sidebarVisible ? (
            <X className="w-5 h-5" aria-hidden="true" />
          ) : (
            <Menu className="w-5 h-5" aria-hidden="true" />
          )}
        </button>

        {/* Spacer */}
        <div className="hidden lg:block flex-1" />

        {/* Right Section */}
        <div className="flex items-center gap-2 sm:gap-4">
          {/* Dark Mode Toggle */}
          <button
            type="button"
            onClick={toggleTheme}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? (
              <Sun className="w-5 h-5 text-yellow-500" aria-hidden="true" />
            ) : (
              <Moon className="w-5 h-5 text-gray-800 dark:text-gray-200" aria-hidden="true" />
            )}
          </button>

          {/* Quick Chat */}
          <button
            type="button"
            onClick={() => navigate('/chat')}
            className="p-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors text-primary-600 dark:text-primary-400"
            aria-label="Chat with AI Assistant"
          >
            <MessageCircle className="w-5 h-5" aria-hidden="true" />
          </button>

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <button
              type="button"
              onClick={() => setNotificationsOpen((o) => !o)}
              className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
              aria-haspopup="true"
              aria-expanded={notificationsOpen}
            >
              <Bell className="w-5 h-5" aria-hidden="true" />
              {unreadCount > 0 && (
                <span
                  className="absolute -top-1 -right-1 bg-red-500 text-white rounded-full flex items-center justify-center text-xs leading-none"
                  style={{
                    width: unreadCount > 9 ? '1.5rem' : '1.25rem',
                    height: unreadCount > 9 ? '1.5rem' : '1.25rem',
                    fontSize: unreadCount > 9 ? '0.625rem' : '0.75rem',
                  }}
                  aria-hidden="true"
                >
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </button>

            {/* Notifications Dropdown */}
            <AnimatePresence>
              {notificationsOpen && (
                <motion.div
                  className="absolute right-0 mt-2 w-64 md:w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50"
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  role="menu"
                  aria-label="Notifications"
                >
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">Notifications</h3>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {notifications && notifications.length > 0 ? (
                      notifications.slice(0, 5).map((notification) => (
                        <button
                          type="button"
                          key={notification.id}
                          className={`w-full text-left px-4 py-3 border-b border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                            !notification.read ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                          }`}
                          onClick={() => markNotificationAsRead?.(notification.id)}
                          role="menuitem"
                        >
                          <p className="text-sm-fluid font-medium text-gray-900 dark:text-gray-100">
                            {notification.title}
                          </p>
                          <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-1">
                            {notification.message}
                          </p>
                        </button>
                      ))
                    ) : (
                      <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        <Bell className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                        <p>No notifications</p>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Profile */}
          <div className="relative" ref={profileRef}>
            <button
              type="button"
              onClick={() => setProfileOpen((o) => !o)}
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              aria-label="User menu"
              aria-haspopup="true"
              aria-expanded={profileOpen}
            >
              <div className="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm-fluid font-semibold">
                {getInitials(displayName)}
              </div>
              <span className="hidden sm:block text-sm-fluid font-medium text-gray-700 dark:text-gray-200 max-w-[120px] truncate">
                {displayName}
              </span>
            </button>

            {/* Profile Dropdown */}
            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50"
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                  role="menu"
                  aria-label="User menu"
                >
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <p className="text-sm-fluid font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {displayName}
                    </p>
                    <p className="text-sm-fluid text-gray-600 dark:text-gray-400 truncate">
                      {user?.email ?? 'user@example.com'}
                    </p>
                  </div>

                  <div className="py-1">
                    <button
                      type="button"
                      onClick={() => {
                        navigate('/settings')
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-4 py-2 text-sm-fluid text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                      role="menuitem"
                    >
                      <User className="w-4 h-4" aria-hidden="true" />
                      <span>View Profile</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        navigate('/settings')
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-4 py-2 text-sm-fluid text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                      role="menuitem"
                    >
                      <Settings className="w-4 h-4" aria-hidden="true" />
                      <span>Settings</span>
                    </button>

                    <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

                    <button
                      type="button"
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm-fluid text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                      role="menuitem"
                    >
                      <LogOut className="w-4 h-4" aria-hidden="true" />
                      <span>Logout</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </header>
  )
})

// ── Layout ──────────────────────────────────────────────────────────────

export function Layout({ children }: LayoutProps): JSX.Element {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarVisible, setSidebarVisible] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem('fe_sidebar_visible')
      return stored === null ? true : (JSON.parse(stored) as boolean)
    } catch {
      return true
    }
  })

  const location = useLocation()

  // Persist sidebar preference
  useEffect(() => {
    try {
      localStorage.setItem('fe_sidebar_visible', JSON.stringify(sidebarVisible))
    } catch {
      // Storage might not be available
    }
  }, [sidebarVisible])

  // Close mobile sidebar on route change
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  // Escape key closes mobile sidebar
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent): void => {
      if (e.key === 'Escape' && sidebarOpen) {
        setSidebarOpen(false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [sidebarOpen])

  // Determine if current route is an auth-related page where we want to show the page-local header instead
  const authRoutePaths = ['/login', '/register', '/forgot-password', '/reset-password']
  const isAuthRoute = authRoutePaths.includes(location.pathname) || location.pathname.startsWith('/auth')

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Desktop Sidebar */}
      {sidebarVisible && (
        <div className="hidden lg:flex lg:flex-shrink-0">
          <Sidebar isOpen onClose={() => setSidebarOpen(false)} />
        </div>
      )}

      {/* Mobile/Tablet Sidebar */}
      <div className="lg:hidden">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        {!isAuthRoute && (
          <Header
            onMenuClick={() => setSidebarOpen((o) => !o)}
            onDesktopToggle={() => setSidebarVisible((v) => !v)}
            sidebarVisible={sidebarVisible}
          />
        )}

        <main className="flex-1 overflow-auto" id="main-content">
          <div className="min-h-full py-4 sm:py-6">
            <div className="fluid-container">
              {children}
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

// ── PageContainer ───────────────────────────────────────────────────────

export function PageContainer({
  title,
  subtitle,
  action,
  children,
  icon = null,
  showLogo = false,
}: PageContainerProps): JSX.Element {
  const hasIcon = Boolean(icon) || showLogo

  const renderIcon = (): ReactNode => {
    // If no icon requested
    if (icon === null) return null

    // If it's already a React element (JSX), return it directly
    if (isValidElement(icon)) {
      return icon
    }

    // Determine if the provided `icon` is a component type (function or memo/forwardRef object)
    const maybeComp = icon as any
    const isComponentType =
      typeof icon === 'function' ||
      (typeof icon === 'object' &&
        (maybeComp.$$typeof === Symbol.for('react.memo') ||
          maybeComp.$$typeof === Symbol.for('react.forward_ref') ||
          typeof maybeComp.render === 'function'))

    if (isComponentType) {
      const IconComp = icon as IconComponent
      return (
        <div className="card-icon-wrapper" aria-hidden="true">
          <FluidIcon icon={IconComp} size="lg" />
        </div>
      )
    }

    // Fallback: treat as a plain ReactNode
    return icon as ReactNode
  }

  return (
    <div className="space-y-4 sm:space-y-6 w-full">
      {/* Page Header */}
      <div className="flex flex-row items-center justify-between gap-3 sm:gap-4 md:gap-6 flex-wrap">
        <div className="flex-1 min-w-0 flex items-center" style={{ gap: 'var(--header-gap, 0.75rem)' }}>
          {hasIcon && (
            <div
              className="flex-shrink-0 rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center"
              style={{
                width: 'var(--page-icon-size, 2.5rem)',
                height: 'var(--page-icon-size, 2.5rem)',
                boxShadow: '0 6px 18px rgba(15,23,42,0.08)',
              }}
              aria-hidden="true"
            >
              {renderIcon()}
            </div>
          )}
          <div className="min-w-0">
            <h1
              className="font-bold text-gray-900 dark:text-gray-100"
              style={{ fontSize: 'var(--font-xl, 1.5rem)', margin: 0 }}
            >
              {title}
            </h1>
            {subtitle && (
              <p
                className="text-gray-600 dark:text-gray-400 mt-1"
                style={{ fontSize: 'var(--font-sm, 0.875rem)', margin: 0 }}
              >
                {subtitle}
              </p>
            )}
          </div>
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </div>

      {/* Content: provide consistent padding and prevent overflow */}
      <div className="p-4 sm:p-6 lg:p-8 min-w-0 break-words overflow-hidden">{children}</div>
    </div>
  )
}
