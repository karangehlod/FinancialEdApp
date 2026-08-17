/**
 * BudgetsPage — budget management with spend tracking and over-budget alerts.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - CRUD for budgets via useBudgetStore
 *  - Derive spent % and over-budget status reactively
 */

import React, { useEffect, useState, useMemo, useRef, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import { PiggyBank, Plus, Edit2, Trash2, AlertTriangle } from 'lucide-react'

import { Layout, PageContainer } from '@/components/Layout'
import { Button, Input, Select, LoadingSpinner, EmptyState, Modal, FluidIcon } from '@/components/UI'
import { FluidGrid } from '@/components/FluidGrid'
import { useProtectedRoute } from '@/hooks/useAuth'
import { useCurrency } from '@/hooks/useCurrency'
import { useBudgetStore } from '@/store/index'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import type { Budget } from '@/types'

// ── Types ──────────────────────────────────────────────────────────────────

// The store normalises API fields; extend Budget to cover both naming conventions.
type NormalizedBudget = Budget & {
  readonly allocated_amount?: number
  readonly spent_amount?: number
}

interface BudgetFormData {
  category: string
  amount: string
  month: string
  year: string
}

type BudgetFormErrors = Partial<Record<keyof BudgetFormData, string>>

// ── Helpers ────────────────────────────────────────────────────────────────

const getAllocated = (b: NormalizedBudget): number =>
  b.allocated_amount ?? b.amount ?? 0

const getSpent = (b: NormalizedBudget): number =>
  b.spent_amount ?? b.spent ?? 0

const spentPct = (b: NormalizedBudget): number => {
  const alloc = getAllocated(b)
  return alloc > 0 ? Math.min((getSpent(b) / alloc) * 100, 100) : 0
}

const BUDGET_CATEGORIES = [
  { value: 'food', label: 'Food & Dining' },
  { value: 'transport', label: 'Transportation' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'health', label: 'Health & Fitness' },
  { value: 'education', label: 'Education' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'other', label: 'Other' },
]

const MONTHS = [
  { value: '1', label: 'January' }, { value: '2', label: 'February' },
  { value: '3', label: 'March' },   { value: '4', label: 'April' },
  { value: '5', label: 'May' },     { value: '6', label: 'June' },
  { value: '7', label: 'July' },    { value: '8', label: 'August' },
  { value: '9', label: 'September' },{ value: '10', label: 'October' },
  { value: '11', label: 'November' },{ value: '12', label: 'December' },
]

const currentYear = new Date().getFullYear()
const YEARS = Array.from({ length: 5 }, (_, i) => {
  const y = currentYear - 2 + i
  return { value: String(y), label: String(y) }
})

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

interface ProgressBarProps {
  pct: number
  isOver: boolean
}

const ProgressBar: React.FC<ProgressBarProps> = ({ pct, isOver }) => (
  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2 mt-2">
    <div
      className={`h-2 rounded-full transition-all duration-500 ${isOver ? 'bg-red-500' : pct > 80 ? 'bg-yellow-500' : 'bg-green-500'}`}
      style={{ width: `${pct}%` }}
    />
  </div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const BudgetsPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)

  const { budgets, fetchBudgets, createBudget, updateBudget, deleteBudget, isLoading: budgetsLoading } = useBudgetStore()

  const now = new Date()
  const [filterMonth, setFilterMonth] = useState(String(now.getMonth() + 1))
  const [filterYear, setFilterYear]   = useState(String(now.getFullYear()))
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId]     = useState<number | null>(null)
  const [formData, setFormData]       = useState<BudgetFormData>({
    category: '',
    amount: '',
    month: String(now.getMonth() + 1),
    year: String(now.getFullYear()),
  })
  const [formErrors, setFormErrors] = useState<BudgetFormErrors>({})

  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchBudgets().catch(console.error)
    }
  }, [isAuthenticated, fetchBudgets])

  // ── Derived data ───────────────────────────────────────────────────────

  const filteredBudgets = useMemo((): NormalizedBudget[] => {
    const m = parseInt(filterMonth, 10)
    const y = parseInt(filterYear, 10)
    return (budgets as NormalizedBudget[]).filter(
      (b) => b.month === m && b.year === y,
    )
  }, [budgets, filterMonth, filterYear])

  const summary = useMemo(() => {
    const totalAllocated = filteredBudgets.reduce((s, b) => s + getAllocated(b), 0)
    const totalSpent     = filteredBudgets.reduce((s, b) => s + getSpent(b), 0)
    const overBudget     = filteredBudgets.filter((b) => getSpent(b) > getAllocated(b)).length
    return { totalAllocated, totalSpent, overBudget }
  }, [filteredBudgets])

  // ── Handlers ───────────────────────────────────────────────────────────

  const validateForm = useCallback((): BudgetFormErrors => {
    const errors: BudgetFormErrors = {}
    if (!formData.category) errors.category = 'Category is required'
    if (!formData.amount) errors.amount = 'Amount is required'
    else if (parseFloat(formData.amount) <= 0) errors.amount = 'Amount must be positive'
    if (!formData.month) errors.month = 'Month is required'
    if (!formData.year) errors.year = 'Year is required'
    return errors
  }, [formData])

  const resetForm = useCallback(() => {
    setFormData({ category: '', amount: '', month: String(now.getMonth() + 1), year: String(now.getFullYear()) })
    setFormErrors({})
    setEditingId(null)
  }, [now])

  const handleSubmit = useCallback(async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const errors = validateForm()
    if (Object.keys(errors).length > 0) { setFormErrors(errors); return }

    const payload = {
      category: formData.category,
      amount: parseFloat(formData.amount),
      month: parseInt(formData.month, 10),
      year: parseInt(formData.year, 10),
    }

    try {
      if (editingId !== null) {
        await updateBudget(editingId, payload)
        showSuccessToast('Budget updated')
      } else {
        await createBudget(payload)
        showSuccessToast('Budget created')
      }
      setIsModalOpen(false)
      resetForm()
      fetchBudgets().catch(console.error)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ?? 'Unknown error'
      showErrorToast(editingId !== null ? `Update failed: ${msg}` : `Create failed: ${msg}`)
    }
  }, [formData, validateForm, editingId, updateBudget, createBudget, resetForm, fetchBudgets])

  const handleEdit = useCallback((budget: NormalizedBudget) => {
    setEditingId(budget.id)
    setFormData({
      category: budget.category,
      amount: String(getAllocated(budget)),
      month: String(budget.month),
      year: String(budget.year),
    })
    setIsModalOpen(true)
  }, [])

  const handleDelete = useCallback(async (id: number) => {
    if (!window.confirm('Delete this budget?')) return
    try {
      await deleteBudget(id)
      showSuccessToast('Budget deleted')
    } catch {
      showErrorToast('Failed to delete budget')
    }
  }, [deleteBudget])

  const field = useCallback(
    (key: keyof BudgetFormData) =>
      (e: ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        setFormData((p) => ({ ...p, [key]: e.target.value }))
        setFormErrors((p) => ({ ...p, [key]: '' }))
      },
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

  return (
    <Layout>
      <PageContainer title="Budgets" subtitle="Allocate and track monthly spending" icon={PiggyBank}>

        {/* Filters */}
        <motion.div className="flex gap-4 mb-6 flex-wrap items-end" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <FluidGrid min="180px" className="w-full items-end">
            <Select label="Month" options={MONTHS} value={filterMonth}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterMonth(e.target.value)} />
            <Select label="Year" options={YEARS} value={filterYear}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setFilterYear(e.target.value)} />
          </FluidGrid>
        </motion.div>

        {/* Summary Cards */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
          <FluidGrid min="200px" className="gap-4">
            <SummaryCard label="Total Allocated" value={formatCurrency(summary.totalAllocated)}
              subtext={`${filteredBudgets.length} budget(s)`}
              colorClass="border-blue-500"
              gradientClass="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30" />
            <SummaryCard label="Total Spent" value={formatCurrency(summary.totalSpent)}
              subtext={`${summary.totalAllocated > 0 ? ((summary.totalSpent / summary.totalAllocated) * 100).toFixed(0) : 0}% of budget`}
              colorClass="border-green-500"
              gradientClass="bg-gradient-to-r from-green-50 to-teal-50 dark:from-green-900/30 dark:to-teal-900/30" />
            <SummaryCard label="Remaining" value={formatCurrency(Math.max(summary.totalAllocated - summary.totalSpent, 0))}
              subtext={`${summary.overBudget} over-budget categor${summary.overBudget === 1 ? 'y' : 'ies'}`}
              colorClass={summary.overBudget > 0 ? 'border-red-500' : 'border-purple-500'}
              gradientClass={summary.overBudget > 0
                ? 'bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30'
                : 'bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30'} />
          </FluidGrid>
        </motion.div>

        {/* Add CTA */}
        <div className="flex justify-end mb-4">
          <Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary" className="gap-2">
            <FluidIcon icon={Plus} size="sm" />
            Add Budget
          </Button>
        </div>

        {/* Budget List */}
        {budgetsLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : filteredBudgets.length === 0 ? (
          <EmptyState icon={PiggyBank} title="No budgets for this period"
            description="Create a budget to start tracking your spending"
            action={<Button onClick={() => setIsModalOpen(true)} variant="primary">Create Budget</Button>} />
        ) : (
          <motion.div className="space-y-4" role="list" aria-label="Budget list">
            {filteredBudgets.map((budget, i) => {
              const allocated = getAllocated(budget)
              const spent     = getSpent(budget)
              const pct       = spentPct(budget)
              const isOver    = spent > allocated
              const catLabel  = BUDGET_CATEGORIES.find((c) => c.value === budget.category)?.label ?? budget.category

              return (
                <motion.div key={budget.id} role="listitem"
                  className="glass rounded-lg p-4 sm:p-6 hover:shadow-card-hover"
                  initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.05 }} whileHover={{ x: 3 }}>

                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100">{catLabel}</h3>
                        {isOver && (
                          <span className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 font-medium">
                            <AlertTriangle className="w-3 h-3" /> Over budget
                          </span>
                        )}
                      </div>
                      <p className="text-sm-fluid text-gray-500 dark:text-gray-400">
                        {MONTHS.find((m) => m.value === String(budget.month))?.label} {budget.year}
                      </p>
                      <ProgressBar pct={pct} isOver={isOver} />
                      <div className="flex justify-between mt-1 text-xs-fluid text-gray-500 dark:text-gray-400">
                        <span>Spent: {formatCurrency(spent)}</span>
                        <span>of {formatCurrency(allocated)} ({pct.toFixed(0)}%)</span>
                      </div>
                    </div>

                    <div className="flex gap-2 flex-shrink-0">
                      <Button size="sm" variant="ghost" className="p-2" onClick={() => handleEdit(budget)} title="Edit">
                        <FluidIcon icon={Edit2} size="sm" />
                      </Button>
                      <Button size="sm" variant="ghost" className="p-2 text-red-600" onClick={() => handleDelete(budget.id)} title="Delete">
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
        title={editingId !== null ? 'Edit Budget' : 'Add Budget'} className="max-w-sm">
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Select label="Category" options={BUDGET_CATEGORIES} value={formData.category}
            onChange={field('category') as (e: ChangeEvent<HTMLSelectElement>) => void}
            error={formErrors.category} />
          <Input label="Monthly Limit ($)" type="number" placeholder="0.00" step="0.01"
            value={formData.amount} onChange={field('amount') as (e: ChangeEvent<HTMLInputElement>) => void}
            error={formErrors.amount} />
          <Select label="Month" options={MONTHS} value={formData.month}
            onChange={field('month') as (e: ChangeEvent<HTMLSelectElement>) => void}
            error={formErrors.month} />
          <Select label="Year" options={YEARS} value={formData.year}
            onChange={field('year') as (e: ChangeEvent<HTMLSelectElement>) => void}
            error={formErrors.year} />
          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={budgetsLoading}>
              {editingId !== null ? 'Update' : 'Create'} Budget
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
