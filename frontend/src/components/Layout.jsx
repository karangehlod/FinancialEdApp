import React, { useState, useRef, useEffect } from 'react'
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
import { useAuthStore } from '../store/authStore'
import { useNotificationStore } from '../store/index'
import { useThemeStore } from '../store/themeStore'
import { getInitials } from '../utils/helpers'
import { Button } from './UI'
import FinEdLogo from '../assets/FinEdLogo.png'

/**
 * Optimized Sidebar Navigation Component - Memoized to prevent unnecessary re-renders
 */
export const Sidebar = React.memo(({ isOpen, onClose }) => {
  const navigate = useNavigate()
  const location = useLocation()
  const { logout } = useAuthStore()

  const { user } = useAuthStore()

  // Build nav items dynamically — show Admin only for admin users
  const adminEmails = (import.meta.env.VITE_ADMIN_EMAILS || '').split(',').map(e => e.trim().toLowerCase()).filter(Boolean)
  const isAdmin = user?.email && adminEmails.includes(user.email.toLowerCase())

  const navItems = [
    { label: 'Dashboard', icon: Home, path: '/dashboard' },
    { label: 'Expenses', icon: Wallet, path: '/expenses' },
    { label: 'Budgets', icon: PieChart, path: '/budgets' },
    { label: 'Loans', icon: Zap, path: '/loans' },
    { label: 'Goals', icon: Target, path: '/goals' },
    { label: 'Reports', icon: BarChart3, path: '/reports' },
    { label: 'Chat', icon: MessageCircle, path: '/chat' },
    { label: 'Settings', icon: Settings, path: '/settings' },
    ...(isAdmin ? [{ label: 'Admin', icon: Shield, path: '/admin' }] : []),
  ]

  const isActive = (path) => location.pathname === path

  const handleLogout = () => {
    // Auth store's logout handles token cleanup and performs the redirect.
    logout()
  }

  const handleNavigation = (path) => {
    navigate(path)
    onClose?.()
  }

  return (
    <>
      {/* Mobile/Tablet Overlay */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            className="fixed inset-0 bg-black bg-opacity-50 lg:hidden z-40"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            aria-hidden="true"
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        className={`
          fixed lg:static inset-y-0 left-0 z-50
          w-56 sm:w-64 bg-gradient-to-b from-primary-900 to-primary-800
          text-white shadow-xl
          transform transition-transform lg:translate-x-0
          flex flex-col h-full
          overflow-hidden
          ${isOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
        initial={false}
        animate={{ x: isOpen ? 0 : -256 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      >
        {/* Header */}
        <div className="border-b border-primary-700 flex-shrink-0">
          <div className="flex items-center justify-between" style={{ paddingLeft: '0', paddingRight: '0' }}>
             <motion.div
               initial={{ opacity: 0 }}
               animate={{ opacity: 1 }}
             >
               {/* Logo-only sidebar header: center the logo and let CSS --sidebar-logo-size control sizing */}
               <div className="sidebar-brand flex items-center justify-start w-full" style={{ minHeight: 'var(--sidebar-brand-height)' }}>
                 <img
                   src={FinEdLogo}
                   alt="FinEd"
                   className="object-contain rounded sidebar-logo"
                 />
                 <div className="brand-text" style={{ marginLeft: 'calc(var(--header-gap) * 0.5)' }}>
                   <h1 className="font-bold gradient-text" style={{ fontSize: 'var(--sidebar-title-size)', lineHeight: 1 }}>{'FinEd'}</h1>
                   <p className="text-primary-200 hidden sm:block" style={{ fontSize: 'var(--sidebar-subtitle-size)', margin: 0 }}>Master Your Money</p>
                 </div>
               </div>
             </motion.div>
             <button 
               onClick={onClose} 
               className="lg:hidden p-1 hover:bg-primary-700 rounded-lg transition-colors"
               aria-label="Close menu"
             >
               <X size={24} />
             </button>
           </div>
         </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto p-6 space-y-2">
          {navItems.map((item, index) => {
            const Icon = item.icon
            const active = isActive(item.path)

            return (
              <motion.button
                key={item.path}
                onClick={() => handleNavigation(item.path)}
                className={`
                  w-full flex items-center gap-3 px-4 py-3 rounded-lg
                  transition-all duration-200 text-left
                  ${
                    active
                      ? 'bg-white bg-opacity-20 text-white'
                      : 'text-primary-200 hover:text-white hover:bg-white hover:bg-opacity-10'
                  }
                `}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ x: 4 }}
              >
                <Icon size={20} className="flex-shrink-0" />
                <span className="font-medium flex-1 min-w-0 truncate">{item.label}</span>
              </motion.button>
            )
          })}
        </nav>

        {/* Logout Button */}
        <div className="p-6 border-t border-primary-700 flex-shrink-0">
          <Button
            onClick={handleLogout}
            variant="secondary"
            className="w-full text-primary-600 border-primary-200 hover:bg-primary-50"
          >
            <LogOut size={18} />
            <span>Logout</span>
          </Button>
          {/* Owner Info */}
          <p className="mt-4 text-center text-xs sm:text-sm text-primary-400">
            Built by <span className="font-semibold text-primary-200">Karan Gehlod</span><br />
            <a href="mailto:support+theprodsde@gmail.com" className="hover:text-white transition-colors">
              support+theprodsde@gmail.com
            </a>
          </p>
        </div>
      </motion.aside>
    </>
  )
})

/**
 * Optimized Header Component - Memoized to prevent unnecessary re-renders
 */
export const Header = React.memo(({ onMenuClick, onDesktopToggle, sidebarVisible }) => {
  const { user, logout } = useAuthStore()
  const { notifications, markNotificationAsRead } = useNotificationStore()
  const { toggleTheme, theme } = useThemeStore()
  const isDark = theme === 'dark'
  const unreadCount = notifications?.filter((n) => !n.read).length || 0
  // Responsive badge sizing: slightly larger container for 2+ digits, keep text tight
  const notificationBadgeClass = unreadCount > 9
    ? 'absolute -top-1 -right-1 bg-red-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-[10px] leading-none overflow-hidden'
    : 'absolute -top-1 -right-1 bg-red-500 text-white rounded-full flex items-center justify-center text-xs leading-none overflow-hidden' + ''

  // Ensure we apply size via inline style where badge is rendered
  const badgeStyle = {
    width: unreadCount > 9 ? '1.5rem' : '1.25rem',
    height: unreadCount > 9 ? '1.5rem' : '1.25rem',
  }

  const navigate = useNavigate()
  const [profileOpen, setProfileOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const profileRef = useRef(null)
  const notificationsRef = useRef(null)

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (profileRef.current && !profileRef.current.contains(event.target)) {
        setProfileOpen(false)
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target)) {
        setNotificationsOpen(false)
      }
    }

    if (profileOpen || notificationsOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [profileOpen, notificationsOpen])

  const handleLogout = () => {
    // Centralized logout (authStore.logout) performs redirect and cleanup
    logout()
  }

  return (
    <motion.header
      className="app-header bg-white dark:bg-gray-900 shadow-sm border-b border-gray-200 dark:border-gray-700 sticky top-0 z-30 w-full"
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="app-header-inner flex items-center justify-between px-6 py-4">
        {/* Mobile Menu Button */}
        <button 
          onClick={onMenuClick} 
          className="lg:hidden p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          aria-label="Toggle menu"
        >
          <Menu size={24} />
        </button>

        {/* Desktop Sidebar Toggle (persisted preference) */}
        <button
          onClick={onDesktopToggle}
          className="hidden lg:inline-flex p-2 ml-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          aria-label={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
          title={sidebarVisible ? 'Hide sidebar' : 'Show sidebar'}
        >
          {sidebarVisible ? <X size={20} /> : <Menu size={20} />}
        </button>

        {/* Spacer for desktop */}
        <div className="hidden lg:block flex-1" />

        {/* Right Section */}
        <div className="flex items-center gap-4">
          {/* Dark Mode Toggle */}
          <motion.button
            onClick={toggleTheme}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
            whileHover={{ scale: 1.05 }}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {isDark ? <Sun size={20} className="text-yellow-500" /> : <Moon size={20} className="text-gray-800 dark:text-gray-200" />}
          </motion.button>

          {/* Quick Chat Button */}
          <motion.button
            onClick={() => navigate('/chat')}
            className="p-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            title="Chat with AI Assistant"
          >
            <MessageCircle size={20} />
          </motion.button>

          {/* Notifications */}
          <div className="relative" ref={notificationsRef}>
            <motion.button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="relative p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              whileHover={{ scale: 1.05 }}
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className={notificationBadgeClass} aria-hidden="true" style={badgeStyle}>
                  {unreadCount > 99 ? '99+' : (unreadCount > 9 ? '9+' : unreadCount)}
                </span>
              )}
            </motion.button>

            {/* Notifications Dropdown */}
            <AnimatePresence>
              {notificationsOpen && (
                <motion.div
                  className="absolute right-0 mt-2 w-64 md:w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50 overflow-y-auto"
                  style={{ maxHeight: 'var(--placeholder-height)' }}
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                >
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100">Notifications</h3>
                  </div>
                  <div className="max-h-64 overflow-y-auto">
                    {notifications && notifications.length > 0 ? (
                      notifications.slice(0, 5).map((notification) => (
                        <div
                          key={notification.id}
                          className={`px-4 py-3 border-b border-gray-100 dark:border-gray-700 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700 ${
                            !notification.read ? 'bg-blue-50 dark:bg-blue-900/30' : ''
                          }`}
                          onClick={() => markNotificationAsRead?.(notification.id)}
                        >
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">{notification.title}</p>
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">{notification.message}</p>
                        </div>
                      ))
                    ) : (
                      <div className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                        <Bell size={24} className="mx-auto mb-2 opacity-50" />
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
            <motion.button
              onClick={() => setProfileOpen(!profileOpen)}
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
              whileHover={{ scale: 1.05 }}
            >
              <div className="w-8 h-8 bg-primary-600 text-white rounded-full flex items-center justify-center text-sm font-semibold">
                {getInitials(user?.name || [user?.first_name, user?.last_name].filter(Boolean).join(' '))}
              </div>
              <span className="hidden sm:block text-sm font-medium text-gray-700 dark:text-gray-200">
                {user?.name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'User'}
              </span>
            </motion.button>

            {/* Profile Dropdown */}
            <AnimatePresence>
              {profileOpen && (
                <motion.div
                  className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden z-50"
                  initial={{ opacity: 0, y: -10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.95 }}
                >
                  <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{user?.name || [user?.first_name, user?.last_name].filter(Boolean).join(' ') || 'User'}</p>
                    <p className="text-xs text-gray-600 dark:text-gray-400">{user?.email || 'user@example.com'}</p>
                  </div>

                  <div className="py-2">
                    <button
                      onClick={() => {
                        navigate('/profile')
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      <User size={16} />
                      <span>View Profile</span>
                    </button>

                    <button
                      onClick={() => {
                        navigate('/settings')
                        setProfileOpen(false)
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
                    >
                      <Settings size={16} />
                      <span>Settings</span>
                    </button>

                    <div className="border-t border-gray-200 dark:border-gray-700 my-2" />

                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                    >
                      <LogOut size={16} />
                      <span>Logout</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </motion.header>
  )
})

/**
 * Optimized Main Layout Component
 */
export const Layout = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // Desktop sidebar visibility persisted per-user preference
  const [sidebarVisible, setSidebarVisible] = useState(() => {
    try {
      const stored = localStorage.getItem('fe_sidebar_visible')
      return stored === null ? true : JSON.parse(stored)
    } catch (e) {
      return true
    }
  })

  useEffect(() => {
    try { localStorage.setItem('fe_sidebar_visible', JSON.stringify(sidebarVisible)) } catch (e) {}
  }, [sidebarVisible])

  const location = useLocation()

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false)
  }, [location])

  // Handle escape key to close sidebar
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && sidebarOpen) {
        setSidebarOpen(false)
      }
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [sidebarOpen])

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-950">
      {/* Sidebar - Desktop visibility respects user preference */}
      {sidebarVisible && (
        <div className="hidden lg:flex lg:flex-shrink-0">
          <Sidebar isOpen={true} onClose={() => {}} />
        </div>
      )}
      
      {/* Mobile/Tablet Sidebar */}
      <div className="lg:hidden">
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Header */}
        <Header
          onMenuClick={() => setSidebarOpen(!sidebarOpen)}
          onDesktopToggle={() => setSidebarVisible(v => !v)}
          sidebarVisible={sidebarVisible}
        />

        {/* Page Content - Centered with max width */}
        <main className="flex-1 overflow-auto">
          <motion.div
            className="min-h-full px-3 sm:px-6 lg:px-8 py-6"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="max-w-full sm:max-w-4xl md:max-w-6xl lg:max-w-7xl mx-auto">
              {children}
            </div>
          </motion.div>
        </main>
      </div>
    </div>
  )
}

/**
 * Page Container Component - Optimized
 */
export const PageContainer = ({ title, subtitle, action, children, icon = null, iconSize = 'var(--page-icon-size)', iconAlt = 'FinEd logo', showLogo = false }) => {
  // Determine if we have an icon to show (either a component, a valid React node, or the brand logo)
  const IconComp = (icon && typeof icon === 'function') ? icon : null
  const hasIcon = Boolean(icon) || Boolean(showLogo)

  const safeRenderIcon = () => {
    try {
      // If the icon is a valid React element, clone and apply sizing
      if (React.isValidElement(icon)) {
        return React.cloneElement(icon, { style: { width: '70%', height: '70%' }, 'aria-hidden': true })
      }

      // If icon is a component (function or object), create element with sizing
      if (icon) {
        try {
          return React.createElement(icon, { style: { width: '70%', height: '70%' }, 'aria-hidden': true })
        } catch (e) {
          // fallthrough
        }
      }

      // Fallback to brand logo when requested
      if (showLogo) {
        return <img src={FinEdLogo} alt={iconAlt || 'FinEd'} style={{ width: '80%', height: '80%' }} className="object-contain" />
      }

      return null
    } catch (err) {
      // Log and fallback to avoid crashing the whole app due to invalid icon types
      // eslint-disable-next-line no-console
      console.warn('PageContainer: icon render failed, falling back to null or logo', err, icon)
      return showLogo ? <img src={FinEdLogo} alt={iconAlt || 'FinEd'} style={{ width: '80%', height: '80%' }} className="object-contain" /> : null
    }
  }

  return (
    <div className="space-y-6 w-full">
      {/* Page Header */}
      <motion.div
        className="flex flex-row items-center justify-between gap-3 sm:gap-4 md:gap-6 flex-wrap"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <div className="flex-1 min-w-0 flex items-center min-w-0" style={{ gap: 'var(--header-gap)' }}>
          {/* Icon slot - accepts a React node or falls back to the brand logo. Render as a boxed square with outer shadow and no inner shadow. */}
          <div
            className={`flex-shrink-0 rounded-lg bg-white dark:bg-gray-800 flex items-center justify-center ${hasIcon ? '' : 'hidden'}`}
            style={{ width: iconSize, height: iconSize, boxShadow: '0 6px 18px rgba(15,23,42,0.08)' }}
            aria-hidden={!hasIcon}
          >
            {safeRenderIcon()}
          </div>
          <div className="min-w-0">
            <h1 className="font-bold text-gray-900 dark:text-gray-100" style={{ fontSize: 'var(--font-xl)', margin: 0 }}>{title}</h1>
            {subtitle && <p className="text-gray-600 dark:text-gray-400 mt-1 sm:mt-2" style={{ fontSize: 'var(--font-sm)', margin: 0 }}>{subtitle}</p>}
          </div>
        </div>
        {action && <div className="flex-shrink-0">{action}</div>}
      </motion.div>

      {/* Content */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
      >
        {children}
      </motion.div>
    </div>
  )
}
