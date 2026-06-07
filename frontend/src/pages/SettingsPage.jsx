import React, { useState, useEffect } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { Card, Button, Input, Alert, LoadingSpinner } from '../components/UI'
import { useAuthStore } from '../store/authStore'
import { useProfileStore } from '../store/index'
import { IncomeManager } from '../components/financial/IncomeManager'
import { motion } from 'framer-motion'
import {
  Settings,
  LogOut,
  User,
  Lock,
  Bell,
  FileText,
  DollarSign,
  Shield,
  Copy,
  Check,
} from 'lucide-react'
import { showSuccessToast, showErrorToast } from '../utils/toast'
import { authService } from '../services/apiService'
import { useNavigate } from 'react-router-dom'

export const SettingsPage = () => {
  const { isAuthenticated, isLoading: authLoading } = useProtectedRoute()
  const { user, logout, fetchCurrentUser } = useAuthStore()
  const { updateProfile, updateFinancialProfile, fetchFinancialProfile, financialProfile, currency, setCurrency, isLoading: profileLoading } = useProfileStore()
  const navigate = useNavigate()

  const [activeTab, setActiveTab] = useState('profile')
  const [isLoading, setIsLoading] = useState(false)
  const [profileData, setProfileData] = useState({
    first_name: '',
    last_name: '',
    email: '',
  })
  const [passwordData, setPasswordData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })
  const [preferences, setPreferences] = useState({
    currency: 'USD',
    notifications: true,
    emailAlerts: true,
    monthlyReport: true,
  })
  const [financialData, setFinancialData] = useState({
    monthly_salary: 0,
    currency: 'USD',
    rent: 0,
    insurance: 0,
    subscriptions: 0,
  })

  // 2FA state
  const [twoFaStatus, setTwoFaStatus] = useState('idle') // idle | setup | confirm | active
  const [twoFaSecret, setTwoFaSecret] = useState(null)
  const [twoFaUri, setTwoFaUri] = useState(null)
  const [twoFaCode, setTwoFaCode] = useState('')
  const [backupCodes, setBackupCodes] = useState([])
  const [twoFaDisablePassword, setTwoFaDisablePassword] = useState('')
  const [twoFaDisableCode, setTwoFaDisableCode] = useState('')

  // Load 2FA status from user object
  useEffect(() => {
    if (user?.totp_enabled) {
      setTwoFaStatus('active')
    }
  }, [user])

  useEffect(() => {
    if (user) {
      setProfileData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        email: user.email || '',
      })
      setPreferences((prev) => ({
        ...prev,
        currency: currency || 'USD',
      }))
    }
  }, [user, currency])

  // Load financial profile data on mount
  useEffect(() => {
    const loadFinancialProfile = async () => {
      try {
        const fp = await fetchFinancialProfile()
        if (fp) {
          setFinancialData({
            monthly_salary: fp.monthly_salary || 0,
            currency: fp.currency || 'USD',
            rent: fp.rent || 0,
            insurance: fp.insurance || 0,
            subscriptions: fp.subscriptions || 0,
          })
        }
      } catch (error) {
        console.warn('Financial profile not found:', error)
      }
    }
    if (user) loadFinancialProfile()
  }, [user, fetchFinancialProfile])

  // ── 2FA handlers ─────────────────────────────────────────────────────
  const handleSetup2FA = async () => {
    setIsLoading(true)
    try {
      const { twoFactorService } = await import('../services/apiService')
      const data = await twoFactorService.setup()
      setTwoFaSecret(data.secret)
      setTwoFaUri(data.provisioning_uri)
      setTwoFaStatus('setup')
    } catch (error) {
      showErrorToast(error.response?.data?.detail || 'Failed to start 2FA setup')
    } finally {
      setIsLoading(false)
    }
  }

  const handleConfirm2FA = async () => {
    if (!twoFaCode || twoFaCode.length < 6) {
      showErrorToast('Enter a valid 6-digit code')
      return
    }
    setIsLoading(true)
    try {
      const { twoFactorService } = await import('../services/apiService')
      const data = await twoFactorService.enable(twoFaCode)
      setBackupCodes(data.backup_codes || [])
      setTwoFaStatus('active')
      showSuccessToast('2FA enabled successfully!')
      setTwoFaCode('')
      await fetchCurrentUser()
    } catch (error) {
      showErrorToast(error.response?.data?.detail || '2FA verification failed')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisable2FA = async () => {
    if (!twoFaDisablePassword || !twoFaDisableCode) {
      showErrorToast('Password and TOTP code are required')
      return
    }
    setIsLoading(true)
    try {
      const { twoFactorService } = await import('../services/apiService')
      await twoFactorService.disable(twoFaDisablePassword, twoFaDisableCode)
      setTwoFaStatus('idle')
      setTwoFaDisablePassword('')
      setTwoFaDisableCode('')
      showSuccessToast('2FA disabled')
      await fetchCurrentUser()
    } catch (error) {
      showErrorToast(error.response?.data?.detail || 'Failed to disable 2FA')
    } finally {
      setIsLoading(false)
    }
  }

  const handleProfileUpdate = async (e) => {
    e.preventDefault()
    // Debug logs replaced with structured logger
    // logger.info('Profile update triggered', { profileData })
    setIsLoading(true)
    try {
      // logger.info('Calling authService.updateProfile...')
      const response = await authService.updateProfile(profileData)
      // logger.info('Update response received', { response })
      // Update local form state from response
      setProfileData({
        first_name: response.first_name || '',
        last_name: response.last_name || '',
        email: response.email || profileData.email,
      })
      // Re-fetch current user so the navbar / Layout picks up the new name
      await fetchCurrentUser()
      showSuccessToast('Profile updated successfully')
    } catch (error) {
      console.error('[SettingsPage] Profile update error:', error)
      showErrorToast('Failed to update profile')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePasswordChange = async (e) => {
    e.preventDefault()
    
    if (passwordData.new_password !== passwordData.confirm_password) {
      showErrorToast('Passwords do not match')
      return
    }

    if (passwordData.new_password.length < 8) {
      showErrorToast('Password must be at least 8 characters long')
      return
    }

    setIsLoading(true)
    try {
      // Call the backend password change endpoint
      await authService.changePassword({
        current_password: passwordData.current_password,
        new_password: passwordData.new_password,
      })
      showSuccessToast('Password changed successfully')
      setPasswordData({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })
    } catch (error) {
      showErrorToast(error.response?.data?.detail || 'Failed to change password')
    } finally {
      setIsLoading(false)
    }
  }

  const handlePreferencesUpdate = async () => {
    setIsLoading(true)
    try {
      // ✅ Save currency to both user profile AND financial profile for persistence
      await updateProfile({
        currency: preferences.currency,
      })
      // ✅ Also update financial profile to ensure currency is persisted
      await updateFinancialProfile({
        currency: preferences.currency,
      })
      // Also update the currency in the store for UI
      setCurrency(preferences.currency)
      showSuccessToast('Preferences updated successfully')
    } catch (error) {
      console.error('Preferences update error:', error)
      showErrorToast('Failed to update preferences')
    } finally {
      setIsLoading(false)
    }
  }

  const handleLogout = () => {
    // authStore.logout performs token cleanup and will redirect to /login
    logout()
  }

  if (authLoading) {
    return (
      <Layout>
        <PageContainer>
          <LoadingSpinner />
        </PageContainer>
      </Layout>
    )
  }

  const tabs = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'income', label: 'Income', icon: DollarSign },
    { id: 'security', label: 'Security', icon: Lock },
    { id: 'preferences', label: 'Preferences', icon: Bell },
    { id: 'legal', label: 'Legal', icon: FileText },
  ]

  return (
    <Layout>
      <PageContainer>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <div className="flex items-center gap-3">
            <Settings className="w-8 h-8 text-primary-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
              <p className="text-gray-600 dark:text-gray-400 mt-1">Manage your account and preferences</p>
            </div>
          </div>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Sidebar Navigation */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-1"
          >
            <Card className="p-4 space-y-2">
              {tabs.map((tab) => {
                const Icon = tab.icon
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all ${
                      activeTab === tab.id
                        ? 'bg-primary-500 text-white'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}
                  >
                    <Icon style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} />
                    <span className="font-medium">{tab.label}</span>
                  </button>
                )
              })}
              <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-all"
                >
                  <LogOut style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} />
                  <span className="font-medium">Logout</span>
                </button>
              </div>
            </Card>
          </motion.div>

          {/* Main Content */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="lg:col-span-3"
          >
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <Card className="p-8">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Profile Information</h2>
                <form onSubmit={handleProfileUpdate} className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        First Name
                      </label>
                      <Input
                        type="text"
                        value={profileData.first_name}
                        onChange={(e) =>
                          setProfileData({ ...profileData, first_name: e.target.value })
                        }
                        placeholder="John"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Last Name
                      </label>
                      <Input
                        type="text"
                        value={profileData.last_name}
                        onChange={(e) =>
                          setProfileData({ ...profileData, last_name: e.target.value })
                        }
                        placeholder="Doe"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Email Address
                    </label>
                    <Input
                      type="email"
                      value={profileData.email}
                      disabled
                      className="bg-gray-50 dark:bg-gray-700"
                      placeholder="john@example.com"
                    />
                    <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
                      Email cannot be changed. Contact support if you need to update it.
                    </p>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      type="submit"
                      disabled={isLoading}
                    >
                      {isLoading ? 'Saving...' : 'Save Changes'}
                    </Button>
                    <Button variant="outline">Cancel</Button>
                  </div>
                </form>
              </Card>
            )}

            {/* Security Tab */}
            {activeTab === 'security' && (
              <div className="space-y-6">
                {/* Password Change Card */}
                <Card className="p-8">
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Change Password</h2>
                  <form onSubmit={handlePasswordChange} className="space-y-6">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Current Password
                      </label>
                      <Input
                        type="password"
                        value={passwordData.current_password}
                        onChange={(e) =>
                          setPasswordData({ ...passwordData, current_password: e.target.value })
                        }
                        placeholder="Enter your current password"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        New Password
                      </label>
                      <Input
                        type="password"
                        value={passwordData.new_password}
                        onChange={(e) =>
                          setPasswordData({ ...passwordData, new_password: e.target.value })
                        }
                        placeholder="Enter your new password"
                      />
                      <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">Must be at least 8 characters long</p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                        Confirm Password
                      </label>
                      <Input
                        type="password"
                        value={passwordData.confirm_password}
                        onChange={(e) =>
                          setPasswordData({ ...passwordData, confirm_password: e.target.value })
                        }
                        placeholder="Confirm your new password"
                      />
                    </div>
                    <div className="flex gap-3 pt-4">
                      <Button type="submit" disabled={isLoading}>
                        {isLoading ? 'Updating...' : 'Change Password'}
                      </Button>
                    </div>
                  </form>
                </Card>

                {/* Two-Factor Authentication Card */}
                <Card className="p-8">
                  <div className="flex items-center gap-3 mb-6">
                    <Shield className="w-6 h-6 text-indigo-600" />
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Two-Factor Authentication</h2>
                  </div>

                  {/* 2FA Status: Not enabled */}
                  {twoFaStatus === 'idle' && (
                    <div>
                      <Alert
                        type="info"
                        message="Add an extra layer of security by enabling 2FA with an authenticator app (Google Authenticator, Authy, etc.)."
                      />
                      <Button onClick={handleSetup2FA} disabled={isLoading} className="mt-4">
                        {isLoading ? 'Starting Setup...' : 'Enable 2FA'}
                      </Button>
                    </div>
                  )}

                  {/* 2FA Status: Setup — show QR code / secret */}
                  {twoFaStatus === 'setup' && (
                    <div className="space-y-4">
                      <Alert
                        type="info"
                        message="Scan the QR code or enter the secret key into your authenticator app, then enter the 6-digit code below to confirm."
                      />
                      {/* QR code area */}
                      <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-6 text-center">
                        <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                          Add to your authenticator app:
                        </p>
                        {twoFaUri && (
                          <img
                            src={`https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(twoFaUri)}`}
                            alt="2FA QR Code"
                            className="mx-auto mb-4 rounded"
                            width={200}
                            height={200}
                          />
                        )}
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">Or enter this secret manually:</p>
                        <code className="inline-block bg-gray-200 dark:bg-gray-600 px-3 py-1 rounded text-sm font-mono mt-1 select-all dark:text-gray-200">
                          {twoFaSecret}
                        </code>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Verification Code
                        </label>
                        <input
                          type="text"
                          inputMode="numeric"
                          maxLength={6}
                          value={twoFaCode}
                          onChange={(e) => setTwoFaCode(e.target.value.replace(/\D/g, ''))}
                          placeholder="000000"
                          className="w-full text-center text-xl font-mono tracking-[0.5em] px-4 py-3 border-2 border-gray-200 dark:border-gray-600 rounded-lg focus:border-indigo-500 focus:outline-none bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                        />
                      </div>
                      <div className="flex gap-3">
                        <Button onClick={handleConfirm2FA} disabled={isLoading || twoFaCode.length < 6}>
                          {isLoading ? 'Verifying...' : 'Verify & Enable'}
                        </Button>
                        <Button variant="outline" onClick={() => setTwoFaStatus('idle')}>
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* 2FA Status: Active */}
                  {twoFaStatus === 'active' && (
                    <div className="space-y-4">
                      <div className="flex items-center gap-2 text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30 px-4 py-3 rounded-lg">
                        <Check style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} />
                        <span className="font-medium">Two-factor authentication is enabled</span>
                      </div>

                      {/* Show backup codes if just generated */}
                      {backupCodes.length > 0 && (
                        <div className="bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-lg p-4">
                          <p className="text-sm font-semibold text-amber-900 dark:text-amber-300 mb-2">
                            ⚠️ Save these backup codes — they won't be shown again:
                          </p>
                          <div className="grid grid-cols-2 gap-2">
                            {backupCodes.map((code, i) => (
                              <code key={i} className="bg-white dark:bg-gray-800 px-3 py-1 rounded text-sm font-mono border dark:border-gray-600 dark:text-gray-200">
                                {code}
                              </code>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Disable 2FA */}
                      <div className="pt-4 border-t border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Disable 2FA</h3>
                        <div className="space-y-3">
                          <Input
                            type="password"
                            value={twoFaDisablePassword}
                            onChange={(e) => setTwoFaDisablePassword(e.target.value)}
                            placeholder="Account password"
                          />
                          <Input
                            type="text"
                            inputMode="numeric"
                            maxLength={8}
                            value={twoFaDisableCode}
                            onChange={(e) => setTwoFaDisableCode(e.target.value)}
                            placeholder="TOTP code or backup code"
                          />
                          <Button
                            variant="danger"
                            onClick={handleDisable2FA}
                            disabled={isLoading || !twoFaDisablePassword || !twoFaDisableCode}
                          >
                            {isLoading ? 'Disabling...' : 'Disable 2FA'}
                          </Button>
                        </div>
                      </div>
                    </div>
                  )}
                </Card>

                {/* Active Sessions */}
                <Card className="p-8">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Active Sessions</h3>
                  <div className="bg-gray-50 dark:bg-gray-700 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">Current Session</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">This device</p>
                      </div>
                      <span className="px-3 py-1 bg-green-100 dark:bg-green-900/40 text-green-800 dark:text-green-400 rounded-full text-sm font-medium">
                        Active
                      </span>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {/* Income Tab */}
            {activeTab === 'income' && (
              <Card className="p-8">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Financial Information</h2>
                <IncomeManager
                  initialIncome={financialData.monthly_salary || financialProfile?.monthly_salary || 0}
                  currency={currency}
                  onSave={async (data) => {
                    try {
                      const updated = await updateFinancialProfile(data)
                      setFinancialData((prev) => ({ ...prev, ...data, monthly_salary: data.monthly_salary || prev.monthly_salary }))
                      showSuccessToast('Income updated successfully')
                    } catch (error) {
                      showErrorToast('Failed to update income')
                      throw error
                    }
                  }}
                  isLoading={isLoading || profileLoading}
                />
              </Card>
            )}

            {/* Preferences Tab */}
            {activeTab === 'preferences' && (
              <Card className="p-8">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Preferences</h2>
                <div className="space-y-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Currency
                    </label>
                    <select
                      value={preferences.currency}
                      onChange={(e) =>
                        setPreferences({ ...preferences, currency: e.target.value })
                      }
                      className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                    >
                      <option value="USD">US Dollar (USD)</option>
                      <option value="EUR">Euro (EUR)</option>
                      <option value="GBP">British Pound (GBP)</option>
                      <option value="INR">Indian Rupee (INR)</option>
                      <option value="JPY">Japanese Yen (JPY)</option>
                    </select>
                  </div>

                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Notifications</h3>
                    
                    <label className="flex items-center gap-3 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.notifications}
                        onChange={(e) =>
                          setPreferences({ ...preferences, notifications: e.target.checked })
                        }
                        className="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
                      />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">In-app Notifications</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Receive notifications within the app
                        </p>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.emailAlerts}
                        onChange={(e) =>
                          setPreferences({ ...preferences, emailAlerts: e.target.checked })
                        }
                        className="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
                      />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">Email Alerts</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Get email notifications for budget alerts and milestones
                        </p>
                      </div>
                    </label>

                    <label className="flex items-center gap-3 p-4 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={preferences.monthlyReport}
                        onChange={(e) =>
                          setPreferences({ ...preferences, monthlyReport: e.target.checked })
                        }
                        className="w-4 h-4 rounded border-gray-300 dark:border-gray-600"
                      />
                      <div>
                        <p className="font-medium text-gray-900 dark:text-gray-100">Monthly Report</p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Receive monthly financial summaries
                        </p>
                      </div>
                    </label>
                  </div>

                  <div className="flex gap-3 pt-4">
                    <Button
                      onClick={handlePreferencesUpdate}
                      disabled={isLoading}
                    >
                      {isLoading ? 'Saving...' : 'Save Preferences'}
                    </Button>
                    <Button variant="outline">Cancel</Button>
                  </div>
                </div>
              </Card>
            )}

            {/* Legal Tab */}
            {activeTab === 'legal' && (
              <Card className="p-8">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Legal</h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Terms of Service</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      By using Financial Education App, you agree to our terms and conditions.
                    </p>
                    <Button variant="outline" size="sm">
                      View Terms of Service
                    </Button>
                  </div>

                  <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Privacy Policy</h3>
                    <p className="text-gray-600 dark:text-gray-400 mb-4">
                      We are committed to protecting your privacy. Learn how we handle your data.
                    </p>
                    <Button variant="outline" size="sm">
                      View Privacy Policy
                    </Button>
                  </div>

                  <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Data & Privacy</h3>
                    <div className="space-y-4 text-gray-600 dark:text-gray-400">
                      <p>
                        <strong className="dark:text-gray-300">Account Data:</strong> You can download a copy of your account data
                        at any time.
                      </p>
                      <p>
                        <strong className="dark:text-gray-300">Data Deletion:</strong> You can request complete deletion of your
                        account and all associated data.
                      </p>
                      <Button variant="outline" size="sm" className="mt-4">
                        Download My Data
                      </Button>
                    </div>
                  </div>

                  <div className="border-t border-gray-200 dark:border-gray-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Danger Zone</h3>
                    <Alert
                      type="error"
                      message="Deleting your account is permanent and cannot be undone."
                    />
                    <Button
                      variant="danger"
                      size="sm"
                      className="mt-4"
                    >
                      Delete Account
                    </Button>
                  </div>
                </div>
              </Card>
            )}
          </motion.div>
        </div>
      </PageContainer>
    </Layout>
  )
}
