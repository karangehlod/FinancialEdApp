/**
 * LoansPage — loan management with EMI display and payoff tracking.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - CRUD for loans via useLoanStore
 *  - Derive EMI, total interest, and payoff date reactively
 */

import React, { useEffect, useState, useMemo, useRef, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import { CreditCard, Plus, Edit2, Trash2 } from 'lucide-react'

import { Layout, PageContainer } from '@/components/Layout'
import { Button, Input, Select, LoadingSpinner, EmptyState, Modal, FluidIcon } from '@/components/UI'
import { FluidGrid } from '@/components/FluidGrid'
import { useProtectedRoute } from '@/hooks/useAuth'
import { useCurrency } from '@/hooks/useCurrency'
import { useLoanStore } from '@/store/index'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import type { Loan, LoanStatus } from '@/types'

// ── Types ──────────────────────────────────────────────────────────────────

// The store normalises API response field names; extend to cover both.
type NormalizedLoan = Loan & {
  readonly principal_amount?: number
  readonly emi_amount?: number
  readonly outstanding_balance?: number
  readonly interest_rate?: number
  readonly loan_term_months?: number
  readonly remaining_months?: number
}

interface LoanFormData {
  name: string
  principal: string
  interest_rate: string
  term_months: string
  start_date: string
}

type LoanFormErrors = Partial<Record<keyof LoanFormData, string>>

// ── Helpers ────────────────────────────────────────────────────────────────

const getPrincipal = (l: NormalizedLoan): number =>
  l.principal_amount ?? l.principal ?? 0

const getRate = (l: NormalizedLoan): number =>
  l.interest_rate ?? 0

const getTerm = (l: NormalizedLoan): number =>
  l.loan_term_months ?? l.term_months ?? 0

const getEMI = (l: NormalizedLoan): number => {
  const stored = l.emi_amount ?? l.monthly_payment
  if (stored && stored > 0) return stored
  // Calculate EMI: P * r * (1+r)^n / ((1+r)^n - 1)
  const p = getPrincipal(l)
  const r = getRate(l) / 100 / 12
  const n = getTerm(l)
  if (!p || !r || !n) return 0
  return (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
}

const getBalance = (l: NormalizedLoan): number =>
  l.outstanding_balance ?? l.remaining_balance ?? getPrincipal(l)

const STATUS_LABELS: Record<LoanStatus, string> = {
  active: 'Active',
  paid_off: 'Paid Off',
  defaulted: 'Defaulted',
}

const STATUS_COLORS: Record<LoanStatus, string> = {
  active: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
  paid_off: 'text-blue-600 dark:text-blue-400 bg-blue-100 dark:bg-blue-900/30',
  defaulted: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
}

const STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'All Loans' },
  { value: 'active', label: 'Active' },
  { value: 'paid_off', label: 'Paid Off' },
  { value: 'defaulted', label: 'Defaulted' },
]

// ── Sub-components ─────────────────────────────────────────────────────────

interface SummaryCardProps {
  label: string
  value: string
  subtext: string
  colorClass: string
  gradientClass: string
}

const SummaryCard: React.FC<SummaryCardProps> = ({ label, value, subtext, colorClass, gradientClass }) => (
  <motion.div
    className={`p-4 sm:p-6 ${gradientClass} rounded-lg border-l-4 ${colorClass}`}
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
  >
    <p className="text-gray-600 dark:text-gray-400 text-sm-fluid mb-2">{label}</p>
    <p className={`text-value font-bold ${colorClass.replace('border-', 'text-')}`}>{value}</p>
    <p className="text-gray-600 dark:text-gray-400 text-xs-fluid sm:text-sm-fluid mt-2">{subtext}</p>
  </motion.div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const LoansPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)

  const { loans, fetchLoans, createLoan, updateLoan, deleteLoan, isLoading: loansLoading } = useLoanStore()

  const [filterStatus, setFilterStatus] = useState<string>('active')
  const [isModalOpen, setIsModalOpen]   = useState(false)
  const [editingId, setEditingId]       = useState<number | null>(null)
  const [formData, setFormData]         = useState<LoanFormData>({
    name: '', principal: '', interest_rate: '', term_months: '',
    start_date: new Date().toISOString().split('T')[0] ?? '',
  })
  const [formErrors, setFormErrors] = useState<LoanFormErrors>({})

  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchLoans().catch(console.error)
    }
  }, [isAuthenticated, fetchLoans])

  // ── Derived data ───────────────────────────────────────────────────────

  const filteredLoans = useMemo((): NormalizedLoan[] => {
    const all = loans as NormalizedLoan[]
    return filterStatus === 'all' ? [...all] : all.filter((l) => l.status === filterStatus)
  }, [loans, filterStatus])

  const summary = useMemo(() => {
    const active = (loans as NormalizedLoan[]).filter((l) => l.status === 'active')
    const totalBalance  = active.reduce((s, l) => s + getBalance(l), 0)
    const totalMonthly  = active.reduce((s, l) => s + getEMI(l), 0)
    const totalPrincipal = active.reduce((s, l) => s + getPrincipal(l), 0)
    return { count: active.length, totalBalance, totalMonthly, totalPrincipal }
  }, [loans])

  // EMI preview while form is open
  const previewEMI = useMemo(() => {
    const p = parseFloat(formData.principal) || 0
    const r = (parseFloat(formData.interest_rate) || 0) / 100 / 12
    const n = parseInt(formData.term_months, 10) || 0
    if (!p || !r || !n) return 0
    return (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1)
  }, [formData.principal, formData.interest_rate, formData.term_months])

  // ── Handlers ───────────────────────────────────────────────────────────

  const validateForm = useCallback((): LoanFormErrors => {
    const errors: LoanFormErrors = {}
    if (!formData.name.trim()) errors.name = 'Name is required'
    if (!formData.principal) errors.principal = 'Principal is required'
    else if (parseFloat(formData.principal) <= 0) errors.principal = 'Must be positive'
    if (!formData.interest_rate) errors.interest_rate = 'Interest rate is required'
    else if (parseFloat(formData.interest_rate) <= 0) errors.interest_rate = 'Must be positive'
    if (!formData.term_months) errors.term_months = 'Loan term is required'
    else if (parseInt(formData.term_months, 10) <= 0) errors.term_months = 'Must be positive'
    if (!formData.start_date) errors.start_date = 'Start date is required'
    return errors
  }, [formData])

  const resetForm = useCallback(() => {
    setFormData({ name: '', principal: '', interest_rate: '', term_months: '',
      start_date: new Date().toISOString().split('T')[0] ?? '' })
    setFormErrors({})
    setEditingId(null)
  }, [])

  const handleSubmit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const errors = validateForm()
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return }

    const payload = {
      name: formData.name.trim(),
      principal: parseFloat(formData.principal),
      interest_rate: parseFloat(formData.interest_rate),
      term_months: parseInt(formData.term_months, 10),
      start_date: formData.start_date,
    }

    try {
      if (editingId !== null) {
        await updateLoan(editingId, payload)
        showSuccessToast('Loan updated')
      } else {
        await createLoan(payload)
        showSuccessToast('Loan added')
      }
      setIsModalOpen(false)
      resetForm()
      fetchLoans().catch(console.error)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ?? 'Unknown error'
      showErrorToast(editingId !== null ? `Update failed: ${msg}` : `Add failed: ${msg}`)
    }
  }, [formData, validateForm, editingId, updateLoan, createLoan, resetForm, fetchLoans])

  const handleEdit = useCallback((loan: NormalizedLoan) => {
    setEditingId(loan.id)
    setFormData({
      name: loan.name,
      principal: String(getPrincipal(loan)),
      interest_rate: String(getRate(loan)),
      term_months: String(getTerm(loan)),
      start_date: loan.start_date?.split('T')[0] ?? '',
    })
    setIsModalOpen(true)
  }, [])

  const handleDelete = useCallback(async (id: number) => {
    if (!window.confirm('Delete this loan?')) return
    try {
      await deleteLoan(id)
      showSuccessToast('Loan deleted')
    } catch {
      showErrorToast('Failed to delete loan')
    }
  }, [deleteLoan])

  const field = useCallback(
    (key: keyof LoanFormData) => (e: ChangeEvent<HTMLInputElement>) => {
      setFormData((p) => ({ ...p, [key]: e.target.value }))
      setFormErrors((p) => ({ ...p, [key]: '' }))
    }, [],
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

  return (
    <Layout>
      <PageContainer title="Loans" subtitle="Track your loans and monthly payments" icon={CreditCard}>

        {/* Filter */}
        <motion.div className="flex gap-4 mb-6 flex-wrap items-end" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="w-52">
            <Select label="Status" options={STATUS_FILTER_OPTIONS} value={filterStatus}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterStatus(e.target.value)} />
          </div>
        </motion.div>

        {/* Summary Cards */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
          <FluidGrid min="200px" className="gap-4">
            <SummaryCard label="Active Loans" value={String(summary.count)}
              subtext={`Total principal: ${formatCurrency(summary.totalPrincipal)}`}
              colorClass="border-blue-500"
              gradientClass="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30" />
            <SummaryCard label="Outstanding Balance" value={formatCurrency(summary.totalBalance)}
              subtext="across all active loans"
              colorClass="border-red-500"
              gradientClass="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30" />
            <SummaryCard label="Monthly Payments (EMI)" value={formatCurrency(summary.totalMonthly)}
              subtext="total due this month"
              colorClass="border-purple-500"
              gradientClass="bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30" />
          </FluidGrid>
        </motion.div>

        {/* Add CTA */}
        <div className="flex justify-end mb-4">
          <Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary" className="gap-2">
            <FluidIcon icon={Plus} size="sm" />
            Add Loan
          </Button>
        </div>

        {/* Loan List */}
        {loansLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : filteredLoans.length === 0 ? (
          <EmptyState icon={CreditCard} title="No loans found"
            description={filterStatus === 'all' ? 'Add your first loan to track it' : `No ${STATUS_LABELS[filterStatus as LoanStatus] ?? filterStatus} loans`}
            action={<Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary">Add Loan</Button>} />
        ) : (
          <motion.div className="space-y-4" role="list" aria-label="Loans list">
            {filteredLoans.map((loan, i) => {
              const emi     = getEMI(loan)
              const balance = getBalance(loan)
              const principal = getPrincipal(loan)
              const paidPct = principal > 0 ? Math.min(((principal - balance) / principal) * 100, 100) : 0
              const remaining = loan.remaining_months ?? getTerm(loan)
              const totalInterest = emi > 0 ? emi * getTerm(loan) - principal : 0

              return (
                <motion.div key={loan.id} role="listitem"
                  className="glass rounded-lg p-4 sm:p-6 hover:shadow-card-hover"
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }} whileHover={{ x: 3 }}>

                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2 flex-wrap">
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{loan.name}</h3>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[loan.status]}`}>
                          {STATUS_LABELS[loan.status]}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-sm-fluid mb-2">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Principal</span>
                          <p className="font-medium">{formatCurrency(principal)}</p>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Rate</span>
                          <p className="font-medium">{getRate(loan).toFixed(2)}% p.a.</p>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Monthly EMI</span>
                          <p className="font-medium text-blue-600 dark:text-blue-400">{formatCurrency(emi)}</p>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Balance</span>
                          <p className="font-medium text-red-600 dark:text-red-400">{formatCurrency(balance)}</p>
                        </div>
                      </div>

                      {/* Payoff progress */}
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-1.5">
                        <div className="h-1.5 rounded-full bg-blue-500 transition-all duration-700"
                          style={{ width: `${paidPct}%` }} />
                      </div>
                      <div className="flex justify-between mt-1 text-xs-fluid text-gray-500 dark:text-gray-400">
                        <span>{paidPct.toFixed(0)}% paid off</span>
                        <span>{remaining} months remaining · Interest: {formatCurrency(Math.max(totalInterest, 0))}</span>
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      <Button size="sm" variant="ghost" className="p-2" onClick={() => handleEdit(loan)} title="Edit">
                        <FluidIcon icon={Edit2} size="sm" />
                      </Button>
                      <Button size="sm" variant="ghost" className="p-2 text-red-600" onClick={() => handleDelete(loan.id)} title="Delete">
                        <FluidIcon icon={Trash2} size="sm" />
                      </Button>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </PageContainer>

      {/* Add / Edit Modal */}
      <Modal isOpen={isModalOpen} onClose={() => { setIsModalOpen(false); resetForm() }}
        title={editingId !== null ? 'Edit Loan' : 'Add Loan'} className="max-w-sm">
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Input label="Loan Name" type="text" placeholder="e.g., Home Loan"
            value={formData.name} onChange={field('name')} error={formErrors.name} />
          <Input label="Principal Amount ($)" type="number" placeholder="0.00" step="0.01"
            value={formData.principal} onChange={field('principal')} error={formErrors.principal} />
          <Input label="Annual Interest Rate (%)" type="number" placeholder="e.g., 8.5" step="0.01"
            value={formData.interest_rate} onChange={field('interest_rate')} error={formErrors.interest_rate} />
          <Input label="Loan Term (months)" type="number" placeholder="e.g., 240"
            value={formData.term_months} onChange={field('term_months')} error={formErrors.term_months} />
          <Input label="Start Date" type="date"
            value={formData.start_date} onChange={field('start_date')} error={formErrors.start_date} />

          {previewEMI > 0 && (
            <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg text-sm-fluid">
              <span className="text-gray-600 dark:text-gray-400">Estimated monthly EMI: </span>
              <span className="font-semibold text-blue-600 dark:text-blue-400">
                {new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(previewEMI)}
              </span>
            </div>
          )}

          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={loansLoading}>
              {editingId !== null ? 'Update' : 'Add'} Loan
            </Button>
            <Button type="button" variant="secondary" className="flex-1"
              onClick={() => { setIsModalOpen(false); resetForm() }}>
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
    </Layout>
  )
}
