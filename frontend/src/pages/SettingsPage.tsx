/**
 * SettingsPage — user profile, financial settings, theme, security, and data export.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - Profile & financial profile edits via profileStore / authService
 *  - Theme toggle via themeStore
 *  - Password change via authService
 *  - Data export via exportService
 */

import React, { useEffect, useRef, useState, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import { Settings, User, DollarSign, Shield, Moon, Sun, Monitor, Download } from 'lucide-react'

import { Layout, PageContainer } from '@/components/Layout'
import { Button, Input, Select, LoadingSpinner, FluidIcon } from '@/components/UI'
import { FluidGrid } from '@/components/FluidGrid'
import { useProtectedRoute } from '@/hooks/useAuth'
import { useAuthStore } from '@/store/authStore'
import { useProfileStore } from '@/store/index'
import { useThemeStore } from '@/store/themeStore'
import { authService } from '@/services/apiService'
import { exportService } from '@/services/exportService'
import { useExpenseStore } from '@/store/index'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import type { Theme } from '@/types'

// ── Constants ──────────────────────────────────────────────────────────────

const CURRENCIES = [
  { value: 'USD', label: 'USD — US Dollar' },
  { value: 'EUR', label: 'EUR — Euro' },
  { value: 'GBP', label: 'GBP — British Pound' },
  { value: 'INR', label: 'INR — Indian Rupee' },
  { value: 'AUD', label: 'AUD — Australian Dollar' },
  { value: 'CAD', label: 'CAD — Canadian Dollar' },
  { value: 'JPY', label: 'JPY — Japanese Yen' },
]

// ── Sub-components ─────────────────────────────────────────────────────────

interface SectionCardProps {
  title: string
  icon: React.ComponentType<{ className?: string }>
  children: React.ReactNode
}

const SectionCard: React.FC<SectionCardProps> = ({ title, icon: Icon, children }) => (
  <motion.div className="glass rounded-lg p-4 sm:p-6"
    initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
    <div className="flex items-center gap-2 mb-4">
      <Icon className="w-5 h-5 text-blue-500" />
      <h2 className="font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
    </div>
    {children}
  </motion.div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const SettingsPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { user } = useAuthStore()
  const { profile, financialProfile, fetchProfile, fetchFinancialProfile, updateProfile, updateFinancialProfile, isLoading: profileLoading } = useProfileStore()
  const { theme, setTheme } = useThemeStore()
  const { expenses } = useExpenseStore()
  const dataFetchedRef = useRef(false)

  // ── Profile form ───────────────────────────────────────────────────────

  const [profileForm, setProfileForm] = useState({ first_name: '', last_name: '', currency: 'USD' })
  const [profileSaving, setProfileSaving] = useState(false)

  // ── Financial profile form ─────────────────────────────────────────────

  const [finForm, setFinForm] = useState({ monthly_salary: '', monthly_rent: '', monthly_insurance: '', currency: 'USD' })
  const [finSaving, setFinSaving] = useState(false)

  // ── Password form ──────────────────────────────────────────────────────

  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' })
  const [pwSaving, setPwSaving] = useState(false)
  const [pwError, setPwError] = useState('')

  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchProfile().catch(console.error)
      fetchFinancialProfile().catch(console.error)
    }
  }, [isAuthenticated, fetchProfile, fetchFinancialProfile])

  // Sync form when profile loads
  useEffect(() => {
    if (profile) {
      setProfileForm({
        first_name: profile.first_name ?? '',
        last_name: profile.last_name ?? '',
        currency: profile.currency ?? 'USD',
      })
    }
  }, [profile])

  useEffect(() => {
    if (financialProfile) {
      setFinForm({
        monthly_salary: financialProfile.monthly_salary != null ? String(financialProfile.monthly_salary) : '',
        monthly_rent: financialProfile.monthly_rent != null ? String(financialProfile.monthly_rent) : '',
        monthly_insurance: financialProfile.monthly_insurance != null ? String(financialProfile.monthly_insurance) : '',
        currency: financialProfile.currency ?? 'USD',
      })
    }
  }, [financialProfile])

  // ── Handlers ───────────────────────────────────────────────────────────

  const handleProfileSave = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setProfileSaving(true)
    try {
      await updateProfile({ first_name: profileForm.first_name, last_name: profileForm.last_name, currency: profileForm.currency })
      showSuccessToast('Profile updated')
    } catch {
      showErrorToast('Failed to update profile')
    } finally {
      setProfileSaving(false)
    }
  }, [profileForm, updateProfile])

  const handleFinSave = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setFinSaving(true)
    try {
      await updateFinancialProfile({
        monthly_salary: finForm.monthly_salary ? parseFloat(finForm.monthly_salary) : null,
        monthly_rent: finForm.monthly_rent ? parseFloat(finForm.monthly_rent) : null,
        monthly_insurance: finForm.monthly_insurance ? parseFloat(finForm.monthly_insurance) : null,
        currency: finForm.currency,
      })
      showSuccessToast('Financial profile updated')
    } catch {
      showErrorToast('Failed to update financial profile')
    } finally {
      setFinSaving(false)
    }
  }, [finForm, updateFinancialProfile])

  const handlePasswordChange = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setPwError('')
    if (!pwForm.current) { setPwError('Current password is required'); return }
    if (!pwForm.next) { setPwError('New password is required'); return }
    if (pwForm.next.length < 8) { setPwError('New password must be at least 8 characters'); return }
    if (pwForm.next !== pwForm.confirm) { setPwError('Passwords do not match'); return }
    setPwSaving(true)
    try {
      await authService.changePassword({ current_password: pwForm.current, new_password: pwForm.next })
      showSuccessToast('Password changed successfully')
      setPwForm({ current: '', next: '', confirm: '' })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Failed to change password'
      showErrorToast(msg)
    } finally {
      setPwSaving(false)
    }
  }, [pwForm])

  const handleExportCSV = useCallback(() => {
    try {
      exportService.exportExpensesCSV(expenses.map((e) => ({ ...e })), 'my_expenses')
      showSuccessToast('Expenses exported as CSV')
    } catch {
      showErrorToast('Export failed')
    }
  }, [expenses])

  const handleExportJSON = useCallback(() => {
    try {
      exportService.exportToJSON('my_expenses', expenses.map((e) => ({ ...e })))
      showSuccessToast('Expenses exported as JSON')
    } catch {
      showErrorToast('Export failed')
    }
  }, [expenses])

  const profileField = useCallback(
    (key: 'first_name' | 'last_name' | 'currency') =>
      (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
        setProfileForm((p) => ({ ...p, [key]: e.target.value })),
    [],
  )

  const finField = useCallback(
    (key: 'monthly_salary' | 'monthly_rent' | 'monthly_insurance' | 'currency') =>
      (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
        setFinForm((p) => ({ ...p, [key]: e.target.value })),
    [],
  )

  // ── Guard ──────────────────────────────────────────────────────────────

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    )
  }

  if (profileLoading && !profile) {
    return (
      <Layout>
        <PageContainer title="Settings" subtitle="Manage your preferences" icon={Settings}>
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        </PageContainer>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageContainer title="Settings" subtitle="Manage your account and preferences" icon={Settings}>
        <div className="space-y-6">

          {/* Profile */}
          <SectionCard title="Profile" icon={User}>
            <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mb-4">
              Signed in as <span className="font-medium text-gray-700 dark:text-gray-300">{user?.email}</span>
            </p>
            <form onSubmit={handleProfileSave} className="space-y-4">
              <FluidGrid min="200px" className="gap-4">
                <Input label="First Name" type="text" placeholder="First name"
                  value={profileForm.first_name}
                  onChange={profileField('first_name') as (e: ChangeEvent<HTMLInputElement>) => void} />
                <Input label="Last Name" type="text" placeholder="Last name"
                  value={profileForm.last_name}
                  onChange={profileField('last_name') as (e: ChangeEvent<HTMLInputElement>) => void} />
              </FluidGrid>
              <div className="w-52">
                <Select label="Display Currency" options={CURRENCIES} value={profileForm.currency}
                  onChange={profileField('currency') as (e: ChangeEvent<HTMLSelectElement>) => void} />
              </div>
              <Button type="submit" variant="primary" isLoading={profileSaving} className="w-32">
                Save Profile
              </Button>
            </form>
          </SectionCard>

          {/* Financial Profile */}
          <SectionCard title="Financial Profile" icon={DollarSign}>
            <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mb-4">
              Used for AI advisor context and budget recommendations.
            </p>
            <form onSubmit={handleFinSave} className="space-y-4">
              <FluidGrid min="200px" className="gap-4">
                <Input label="Monthly Salary ($)" type="number" placeholder="0.00" step="0.01"
                  value={finForm.monthly_salary}
                  onChange={finField('monthly_salary') as (e: ChangeEvent<HTMLInputElement>) => void} />
                <Input label="Monthly Rent ($)" type="number" placeholder="0.00" step="0.01"
                  value={finForm.monthly_rent}
                  onChange={finField('monthly_rent') as (e: ChangeEvent<HTMLInputElement>) => void} />
                <Input label="Monthly Insurance ($)" type="number" placeholder="0.00" step="0.01"
                  value={finForm.monthly_insurance}
                  onChange={finField('monthly_insurance') as (e: ChangeEvent<HTMLInputElement>) => void} />
              </FluidGrid>
              <div className="w-52">
                <Select label="Financial Currency" options={CURRENCIES} value={finForm.currency}
                  onChange={finField('currency') as (e: ChangeEvent<HTMLSelectElement>) => void} />
              </div>
              <Button type="submit" variant="primary" isLoading={finSaving} className="w-40">
                Save Finances
              </Button>
            </form>
          </SectionCard>

          {/* Appearance */}
          <SectionCard title="Appearance" icon={Monitor}>
            <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mb-4">Choose your preferred theme.</p>
            <div className="flex gap-3 flex-wrap">
              {(
                [
                  { value: 'light', label: 'Light', icon: Sun },
                  { value: 'dark', label: 'Dark', icon: Moon },
                  { value: 'system', label: 'System', icon: Monitor },
                ] as { value: Theme; label: string; icon: React.ComponentType<{ className?: string }> }[]
              ).map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setTheme(value)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg border-2 transition-all ${
                    theme === value
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 font-medium'
                      : 'border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
          </SectionCard>

          {/* Security */}
          <SectionCard title="Security" icon={Shield}>
            <form onSubmit={handlePasswordChange} className="space-y-4 max-w-sm">
              <Input label="Current Password" type="password" placeholder="••••••••"
                value={pwForm.current}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setPwForm((p) => ({ ...p, current: e.target.value }))} />
              <Input label="New Password" type="password" placeholder="Min 8 characters"
                value={pwForm.next}
                onChange={(e: ChangeEvent<HTMLInputElement>) => { setPwForm((p) => ({ ...p, next: e.target.value })); setPwError('') }} />
              <Input label="Confirm New Password" type="password" placeholder="Re-enter new password"
                value={pwForm.confirm}
                onChange={(e: ChangeEvent<HTMLInputElement>) => { setPwForm((p) => ({ ...p, confirm: e.target.value })); setPwError('') }}
                error={pwError} />
              <Button type="submit" variant="primary" isLoading={pwSaving} className="w-40">
                Change Password
              </Button>
            </form>
          </SectionCard>

          {/* Data Export */}
          <SectionCard title="Data Export" icon={Download}>
            <p className="text-sm-fluid text-gray-500 dark:text-gray-400 mb-4">
              Download a copy of your financial data ({expenses.length} expense{expenses.length !== 1 ? 's' : ''} on record).
            </p>
            <div className="flex gap-3 flex-wrap">
              <Button variant="secondary" className="gap-2" onClick={handleExportCSV}>
                <FluidIcon icon={Download} size="sm" />
                Export as CSV
              </Button>
              <Button variant="secondary" className="gap-2" onClick={handleExportJSON}>
                <FluidIcon icon={Download} size="sm" />
                Export as JSON
              </Button>
            </div>
          </SectionCard>

        </div>
      </PageContainer>
    </Layout>
  )
}
