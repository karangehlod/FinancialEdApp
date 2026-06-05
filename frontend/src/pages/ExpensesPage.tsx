/**
 * ExpensesPage — strict TypeScript, authenticated expense management page.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - Filter/group expenses reactively (useMemo)
 *  - Handle CRUD operations via expenseStore
 *  - Delegate form rendering to sub-components
 */

import React, { useEffect, useState, useMemo, useRef, useCallback, type FormEvent, type ChangeEvent } from 'react'
import { motion } from 'framer-motion'
import { Trash2, Edit2, Plus, Wallet } from 'lucide-react'

import { Layout, PageContainer } from '../components/Layout'
import {
  Button,
  Input,
  Select,
  LoadingSpinner,
  EmptyState,
  Modal,
  FluidIcon,
} from '../components/UI'
import { useProtectedRoute } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import { useExpenseStore, useBudgetStore } from '../store/index'
import { showSuccessToast, showErrorToast } from '../utils/toast'
import type { Expense, ExpenseCategory } from '../types'
import { FluidGrid } from '../components/FluidGrid'

// ── Constants ──────────────────────────────────────────────────────────────

interface CategoryOption {
  readonly value: ExpenseCategory
  readonly label: string
}

const CATEGORIES: CategoryOption[] = [
  { value: 'food', label: 'Food & Dining' },
  { value: 'transport', label: 'Transportation' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'health', label: 'Health & Fitness' },
  { value: 'education', label: 'Education' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'other', label: 'Other' },
]

const VALID_CATEGORIES = CATEGORIES.map((c) => c.value)

const TIME_RANGE_DAYS: Record<string, number> = {
  week: 7,
  month: 30,
  quarter: 90,
  year: 365,
}

// ── Types ──────────────────────────────────────────────────────────────────

interface ExpenseFormData {
  description: string
  amount: string
  category: string
  date: string
}

type ExpenseFormErrors = Partial<Record<keyof ExpenseFormData, string>>

interface ExpenseFilters {
  category: string
  timeRange: string
}

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

export const ExpensesPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)

  const {
    expenses,
    fetchExpenses,
    createExpense,
    updateExpense,
    deleteExpense,
    isLoading: expensesLoading,
  } = useExpenseStore()

  const { fetchBudgets } = useBudgetStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [filters, setFilters] = useState<ExpenseFilters>({ category: '', timeRange: 'all' })
  const [formData, setFormData] = useState<ExpenseFormData>({
    description: '',
    amount: '',
    category: '',
    date: new Date().toISOString().split('T')[0] ?? '',
  })
  const [formErrors, setFormErrors] = useState<ExpenseFormErrors>({})

  // Fetch once when authenticated
  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchExpenses().catch((err) => console.error('Expense fetch error:', err))
    }
  }, [isAuthenticated, fetchExpenses])

  // ── Derived data ───────────────────────────────────────────────────────

  const groupedExpenses = useMemo((): [string, Expense[]][] => {
    let filtered: readonly Expense[] = expenses

    if (filters.timeRange !== 'all') {
      const now = new Date()
      const daysAgo = TIME_RANGE_DAYS[filters.timeRange] ?? 30
      const startDate = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000)
      filtered = filtered.filter((exp) => {
        const expDate = new Date(exp.date)
        return expDate >= startDate && expDate <= now
      })
    }

    if (filters.category.trim() !== '') {
      const selectedCategory = filters.category.toLowerCase().trim()
      filtered = filtered.filter((exp) => (exp.category ?? '').toLowerCase().trim() === selectedCategory)
    }

    const sorted = [...filtered].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

    const grouped: Record<string, Expense[]> = {}
    for (const expense of sorted) {
      const key = expense.date
      const bucket = grouped[key]
      if (bucket) bucket.push(expense)
      else grouped[key] = [expense]
    }

    return Object.entries(grouped)
  }, [expenses, filters])

  const totalExpenses = useMemo(
    () =>
      groupedExpenses.reduce((sum, [, dayExpenses]) => {
        return sum + dayExpenses.reduce((daySum, exp) => daySum + (parseFloat(String(exp.amount)) || 0), 0)
      }, 0),
    [groupedExpenses]
  )

  const currentMonthSummary = useMemo(() => {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)

    let monthlyTotal = 0
    const categoryBreakdown: Record<string, number> = {}

    for (const expense of expenses) {
      const expDate = new Date(expense.date)
      if (expDate >= start && expDate <= end) {
        const amount = parseFloat(String(expense.amount)) || 0
        monthlyTotal += amount
        const category = expense.category ?? 'other'
        categoryBreakdown[category] = (categoryBreakdown[category] ?? 0) + amount
      }
    }
    return { monthlyTotal, categoryBreakdown }
  }, [expenses])

  // ── Handlers ───────────────────────────────────────────────────────────

  const validateForm = useCallback((): ExpenseFormErrors => {
    const errors: ExpenseFormErrors = {}
    if (!formData.description) errors.description = 'Description is required'
    if (!formData.amount) errors.amount = 'Amount is required'
    else if (parseFloat(formData.amount) <= 0) errors.amount = 'Amount must be positive'
    if (!formData.category) errors.category = 'Category is required'
    return errors
  }, [formData])

  const resetForm = useCallback(() => {
    setFormData({
      description: '',
      amount: '',
      category: '',
      date: new Date().toISOString().split('T')[0] ?? '',
    })
    setFormErrors({})
    setEditingId(null)
  }, [])

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      const errors = validateForm()
      if (Object.keys(errors).length > 0) {
        setFormErrors(errors)
        return
      }

      const amount = parseFloat(formData.amount)
      if (!amount || amount <= 0 || isNaN(amount)) {
        showErrorToast('Amount must be a valid positive number')
        return
      }

      const category = formData.category.toLowerCase().trim()
      if (!VALID_CATEGORIES.includes(category as ExpenseCategory)) {
        showErrorToast('Invalid category selected')
        return
      }

      const expensePayload = {
        description: formData.description.trim(),
        amount,
        category: category as ExpenseCategory,
        date: formData.date,
      }

      try {
        if (editingId !== null) {
          await updateExpense(editingId, expensePayload)
          showSuccessToast('Expense updated successfully')
        } else {
          await createExpense(expensePayload)
          showSuccessToast('Expense added successfully')
        }
        setIsModalOpen(false)
        resetForm()
        setTimeout(() => {
          fetchExpenses().catch(console.error)
          fetchBudgets().catch(console.error)
        }, 500)
      } catch (err: unknown) {
        const axiosErr = err as { response?: { data?: { detail?: string; message?: string } }; message?: string }
        const errorMsg =
          axiosErr.response?.data?.detail ??
          axiosErr.response?.data?.message ??
          axiosErr.message ??
          'Unknown error'
        showErrorToast(editingId !== null ? `Update failed: ${errorMsg}` : `Add failed: ${errorMsg}`)
      }
    },
    [formData, validateForm, editingId, updateExpense, createExpense, resetForm, fetchExpenses, fetchBudgets]
  )

  const handleDelete = useCallback(
    async (id: number) => {
      if (!window.confirm('Are you sure you want to delete this expense?')) return
      try {
        await deleteExpense(id)
        showSuccessToast('Expense deleted successfully')
        fetchBudgets().catch(console.error)
      } catch {
        showErrorToast('Failed to delete expense')
      }
    },
    [deleteExpense, fetchBudgets]
  )

  const handleEdit = useCallback((expense: Expense) => {
    if (!expense?.id) {
      showErrorToast('Invalid expense data')
      return
    }
    setEditingId(expense.id)
    setFormData({
      description: expense.description ?? '',
      amount: (parseFloat(String(expense.amount)) || 0).toString(),
      category: expense.category ?? '',
      date: expense.date ?? new Date().toISOString().split('T')[0] ?? '',
    })
    setTimeout(() => setIsModalOpen(true), 0)
  }, [])

  const handleFilterChange = useCallback(
    (field: keyof ExpenseFilters) => (e: ChangeEvent<HTMLSelectElement>) => {
      setFilters((prev) => ({ ...prev, [field]: e.target.value }))
    },
    []
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
      <PageContainer title="Expenses" subtitle="Track your spending" icon={Wallet}>
        {/* Filters */}
        <motion.div
          className="flex gap-4 mb-6 items-end flex-wrap"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <FluidGrid min="220px" className="w-full items-end">
            <div>
              <Select
                label="Time Period"
                options={[
                  { value: 'all', label: 'All Time' },
                  { value: 'week', label: 'Last 7 Days' },
                  { value: 'month', label: 'Last 30 Days' },
                  { value: 'quarter', label: 'Last 90 Days' },
                  { value: 'year', label: 'Last Year' },
                ]}
                value={filters.timeRange}
                onChange={handleFilterChange('timeRange')}
              />
            </div>
            <div>
              <Select
                label="Filter by Category"
                options={[{ value: '', label: 'All Categories' }, ...CATEGORIES]}
                value={filters.category}
                onChange={handleFilterChange('category')}
              />
            </div>
            {/* Apply happens automatically when filter values change */}
          </FluidGrid>
        </motion.div>

        {/* Summary Cards */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
          <FluidGrid min="260px" className="gap-4">
            <SummaryCard
              label="Current Month Total"
              value={formatCurrency(currentMonthSummary.monthlyTotal)}
              subtext={`${Object.keys(currentMonthSummary.categoryBreakdown).length} categories`}
              colorClass="border-blue-500"
              gradientClass="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30"
            />
            {groupedExpenses.length > 0 && (
              <SummaryCard
                label={
                  filters.timeRange === 'week'
                    ? 'Last 7 Days'
                    : filters.timeRange === 'month'
                      ? 'Last 30 Days'
                      : filters.timeRange === 'quarter'
                        ? 'Last 90 Days'
                        : filters.timeRange === 'year'
                          ? 'Last Year'
                          : 'Total Expenses (All Time)'
                }
                value={formatCurrency(totalExpenses)}
                subtext={`${groupedExpenses.reduce((sum, [, dayExpenses]) => sum + dayExpenses.length, 0)} transactions`}
                colorClass="border-red-500"
                gradientClass="bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30"
              />
            )}
          </FluidGrid>
        </motion.div>

        {/* Add Expense CTA */}
        <div className="flex justify-end mb-4">
          <Button onClick={() => { resetForm(); setIsModalOpen(true) }} variant="primary" className="gap-2">
            <FluidIcon icon={Plus} size="sm" />
            Add Expense
          </Button>
        </div>

        {/* Expense List */}
        {expensesLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : groupedExpenses.length === 0 ? (
          <EmptyState
            icon={Plus}
            title="No expenses yet"
            description="Start tracking your expenses to see them here"
            action={
              <Button onClick={() => setIsModalOpen(true)} variant="primary">
                Add First Expense
              </Button>
            }
          />
        ) : (
          <motion.div className="space-y-6" role="list" aria-label="Expenses grouped by date">
            {groupedExpenses.map(([date, dayExpenses], dateIndex) => {
              const dayTotal = dayExpenses.reduce(
                (sum, exp) => sum + (parseFloat(String(exp.amount)) || 0),
                0
              )
              const formattedDate = new Date(date).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })

              return (
                <motion.div
                  key={date}
                  role="listitem"
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: dateIndex * 0.05 }}
                >
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{formattedDate}</h3>
                      <p className="text-sm-fluid text-gray-500 dark:text-gray-400">{dayExpenses.length} transaction(s)</p>
                    </div>
                    <p className="text-lg font-bold text-red-600 dark:text-red-400">{formatCurrency(dayTotal)}</p>
                  </div>

                  <div className="space-y-2">
                    {dayExpenses.map((expense, expIndex) => (
                      <motion.div
                        key={expense.id}
                        className="glass rounded-lg p-4 flex items-center justify-between hover:shadow-card-hover"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: expIndex * 0.02 }}
                        whileHover={{ x: 5 }}
                      >
                        <div className="flex-1">
                          <p className="font-semibold text-gray-900 dark:text-gray-100">{expense.description}</p>
                          <p className="text-sm-fluid text-gray-500 dark:text-gray-400">
                            {CATEGORIES.find((c) => c.value === expense.category)?.label ?? expense.category}
                          </p>
                        </div>
                        <div className="flex items-center gap-4">
                          <p className="text-lg font-bold text-red-600 dark:text-red-400 min-w-24 text-right">
                            {formatCurrency(Number(expense.amount))}
                          </p>
                          <div className="flex gap-2">
                            <Button size="sm" variant="ghost" className="p-2" onClick={() => handleEdit(expense)} title="Edit">
                              <FluidIcon icon={Edit2} size="sm" />
                            </Button>
                            <Button size="sm" variant="ghost" className="p-2 text-red-600" onClick={() => handleDelete(expense.id)} title="Delete">
                              <FluidIcon icon={Trash2} size="sm" />
                            </Button>
                          </div>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </PageContainer>

      {/* Add / Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => { setIsModalOpen(false); resetForm() }}
        title={editingId !== null ? 'Edit Expense' : 'Add Expense'}
        className="max-w-sm"
      >
        <form onSubmit={handleSubmit} className="space-y-4" aria-label={editingId !== null ? 'Edit expense form' : 'Add expense form'} noValidate>
          <Input
            label="Description"
            type="text"
            placeholder="e.g., Coffee at Starbucks"
            value={formData.description}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              setFormData((prev) => ({ ...prev, description: e.target.value }))
              setFormErrors((prev) => ({ ...prev, description: '' }))
            }}
            error={formErrors.description}
          />
          <Input
            label="Amount"
            type="number"
            placeholder="0.00"
            step="0.01"
            value={formData.amount}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              setFormData((prev) => ({ ...prev, amount: e.target.value }))
              setFormErrors((prev) => ({ ...prev, amount: '' }))
            }}
            error={formErrors.amount}
          />
          <Select
            label="Category"
            options={CATEGORIES}
            value={formData.category}
            onChange={(e: ChangeEvent<HTMLSelectElement>) => {
              setFormData((prev) => ({ ...prev, category: e.target.value }))
              setFormErrors((prev) => ({ ...prev, category: '' }))
            }}
            error={formErrors.category}
          />
          <Input
            label="Date"
            type="date"
            value={formData.date}
            onChange={(e: ChangeEvent<HTMLInputElement>) => setFormData((prev) => ({ ...prev, date: e.target.value }))}
          />
          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={expensesLoading}>
              {editingId !== null ? 'Update' : 'Add'} Expense
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => { setIsModalOpen(false); resetForm() }}
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
    </Layout>
  )
}
