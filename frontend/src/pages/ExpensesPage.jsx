import React, { useEffect, useState, useMemo, useRef } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import {
  Card,
  Button,
  Input,
  Select,
  Badge,
  LoadingSpinner,
  EmptyState,
  Modal,
} from '../components/UI'
import { useExpenseStore, useBudgetStore } from '../store/index'
import { motion } from 'framer-motion'
import { Trash2, Edit2, Plus, Filter, Wallet } from 'lucide-react'
import { formatDate, getCategoryColor } from '../utils/helpers'
import { showSuccessToast, showErrorToast } from '../utils/toast'

const CATEGORIES = [
  { value: 'food', label: 'Food & Dining' },
  { value: 'transport', label: 'Transportation' },
  { value: 'utilities', label: 'Utilities' },
  { value: 'entertainment', label: 'Entertainment' },
  { value: 'health', label: 'Health & Fitness' },
  { value: 'education', label: 'Education' },
  { value: 'shopping', label: 'Shopping' },
  { value: 'other', label: 'Other' },
]

export const ExpensesPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)
  const {
    expenses,
    fetchExpenses,
    addExpense,
    updateExpense,
    deleteExpense,
    isLoading: expensesLoading,
  } = useExpenseStore()

  const { fetchBudgets } = useBudgetStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [filters, setFilters] = useState({ category: '', timeRange: 'all' })
  const [formData, setFormData] = useState({
    description: '',
    amount: '',
    category: '',
    date: new Date().toISOString().split('T')[0],
  })
  const [formErrors, setFormErrors] = useState({})
  const [isApplyingFilter, setIsApplyingFilter] = useState(false)

  // Fetch data only once when authenticated
  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchExpenses()
    }
  }, [isAuthenticated])

  // Group expenses by date (most recent first)
  const groupedExpenses = useMemo(() => {
    let filtered = expenses
    
    // Apply time range filter
    if (filters.timeRange !== 'all') {
      const now = new Date()
      const daysMap = { 'week': 7, 'month': 30, 'quarter': 90, 'year': 365 }
      const daysAgo = daysMap[filters.timeRange] || 30
      const startDate = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000)
      
      filtered = filtered.filter((exp) => {
        const expDate = new Date(exp.date)
        return expDate >= startDate && expDate <= now
      })
    }
    
    // Apply category filter if selected
    if (filters.category && filters.category.trim() !== '') {
      const selectedCategory = filters.category.toLowerCase().trim()
      filtered = filtered.filter((exp) => 
        (exp.category || '').toLowerCase().trim() === selectedCategory
      )
    }

    // Sort by date descending
    const sorted = [...filtered].sort((a, b) => new Date(b.date) - new Date(a.date))

    // Group by date
    const grouped = {}
    sorted.forEach((expense) => {
      const dateKey = expense.date
      if (!grouped[dateKey]) {
        grouped[dateKey] = []
      }
      grouped[dateKey].push(expense)
    })

    return Object.entries(grouped)
  }, [expenses, filters])

  const validateForm = () => {
    const errors = {}
    if (!formData.description) errors.description = 'Description is required'
    if (!formData.amount) errors.amount = 'Amount is required'
    else if (parseFloat(formData.amount) <= 0) errors.amount = 'Amount must be positive'
    if (!formData.category) errors.category = 'Category is required'
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
      // Validate amount is positive and properly formatted
      const amount = parseFloat(formData.amount)
      if (amount <= 0 || isNaN(amount)) {
        showErrorToast('Amount must be a valid positive number')
        setFormErrors({ ...formErrors, amount: 'Amount must be a valid positive number' })
        return
      }

      // Prepare payload with all required fields
      const expensePayload = {
        description: formData.description.trim(),
        amount: (amount).toFixed(2), // Send as string to ensure proper Decimal conversion
        category: formData.category.toLowerCase().trim(),
        date: formData.date,
      }

      // Validate category is lowercase
      const validCategories = ['food', 'transport', 'utilities', 'entertainment', 'health', 'education', 'shopping', 'other']
      if (!validCategories.includes(expensePayload.category)) {
        showErrorToast('Invalid category selected')
        return
      }

      if (editingId) {
        // Update existing expense - send all fields
        // logger.info('Updating expense', { editingId, expensePayload })
        await updateExpense(editingId, expensePayload)
        showSuccessToast('Expense updated successfully')
      } else {
        // Create new expense
        // logger.info('Creating expense', { expensePayload })
        await addExpense(expensePayload)
        showSuccessToast('Expense added successfully')
      }
      
      // Close modal and reset form
      setIsModalOpen(false)
      resetForm()
      
      // Refetch to ensure fresh data
      setTimeout(() => {
        // logger.info('Refetching expenses and budgets...')
        fetchExpenses()
        fetchBudgets()  // Refresh budgets to show updated spending
      }, 500)
    } catch (err) {
      console.error('Submit error details:', err)
      const errorMsg = err.response?.data?.detail || err.response?.data?.message || err.message || 'Unknown error'
      console.error('Error message:', errorMsg)
      showErrorToast(
        editingId 
          ? `Update failed: ${errorMsg}` 
          : `Add failed: ${errorMsg}`
      )
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this expense?')) {
      try {
        await deleteExpense(id)
        showSuccessToast('Expense deleted successfully')
        // Refetch budgets after deletion to reflect spending changes
        fetchBudgets()
      } catch (err) {
        showErrorToast('Failed to delete expense')
      }
    }
  }

  const handleEdit = (expense) => {
    // Ensure we have valid data before editing
    if (!expense || !expense.id) {
      showErrorToast('Invalid expense data')
      return
    }
    
    // Set editing state first, then populate form, then open modal
    setEditingId(expense.id)
    setFormData({
      description: expense.description || '',
      amount: (parseFloat(expense.amount) || 0).toString(),
      category: expense.category || '',
      date: expense.date || new Date().toISOString().split('T')[0],
    })
    
    // Small delay to ensure state updates before opening modal
    setTimeout(() => {
      setIsModalOpen(true)
    }, 0)
  }

  const resetForm = () => {
    setFormData({
      description: '',
      amount: '',
      category: '',
      date: new Date().toISOString().split('T')[0],
    })
    setFormErrors({})
    setEditingId(null)
  }

  const handleApplyFilters = () => {
    // Filters are already applied reactively through the useMemo
    // This button is for visual feedback and future batch operations
    setIsApplyingFilter(true)
    setTimeout(() => {
      setIsApplyingFilter(false)
    }, 300)
    
    // Optional: Add analytics tracking or refresh data from backend
    // await fetchExpenses({ timeRange: filters.timeRange, category: filters.category })
  }

  // Calculate total expenses safely, handling any potential NaN values
  const totalExpenses = useMemo(() => {
    return groupedExpenses.reduce((sum, [_, dayExpenses]) => {
      const dayTotal = dayExpenses.reduce((daySum, exp) => {
        const amount = parseFloat(exp?.amount) || 0
        return daySum + amount
      }, 0)
      return sum + dayTotal
    }, 0)
  }, [groupedExpenses])

  // Calculate monthly expense summary - RESPECTS FILTERS (from groupedExpenses which is already filtered)
  const monthlyExpenseSummary = useMemo(() => {
    let monthlyTotal = 0
    const categoryBreakdown = {}
    
    // Use groupedExpenses (already filtered by category and time range)
    groupedExpenses.forEach(([_, dayExpenses]) => {
      dayExpenses.forEach((expense) => {
        const amount = parseFloat(expense?.amount) || 0
        monthlyTotal += amount
        
        const category = expense?.category || 'other'
        categoryBreakdown[category] = (categoryBreakdown[category] || 0) + amount
      })
    })
    
    return { monthlyTotal, categoryBreakdown }
  }, [groupedExpenses])  // ⭐ Changed: Now depends on FILTERED groupedExpenses

  // New: current month totals (calendar month, independent of filters)
  const currentMonthSummary = useMemo(() => {
    const now = new Date()
    const start = new Date(now.getFullYear(), now.getMonth(), 1)
    const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)

    let monthlyTotal = 0
    const categoryBreakdown = {}

    expenses.forEach((expense) => {
      const expDate = new Date(expense.date)
      if (expDate >= start && expDate <= end) {
        const amount = parseFloat(expense?.amount) || 0
        monthlyTotal += amount
        const category = expense?.category || 'other'
        categoryBreakdown[category] = (categoryBreakdown[category] || 0) + amount
      }
    })

    return { monthlyTotal, categoryBreakdown }
  }, [expenses])

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
      <PageContainer
        title="Expenses"
        subtitle="Track your spending"
        icon={Wallet}
        iconSize={'var(--page-icon-size)'}
        iconAlt="Expenses"
      >
        {/* Filters Section */}
        <motion.div
          className="flex gap-4 mb-6 items-end flex-wrap"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Time Range Filter */}
          <div className="flex-1 min-w-[200px]">
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
              onChange={(e) => setFilters({ ...filters, timeRange: e.target.value })}
            />
          </div>

          {/* Category Filter */}
          <div className="flex-1 min-w-[200px]">
            <Select
              label="Filter by Category"
              options={[{ value: '', label: 'All Categories' }, ...CATEGORIES]}
              value={filters.category}
              onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            />
          </div>

          {/* Go Button */}
          <Button
            onClick={handleApplyFilters}
            variant="primary"
            isLoading={isApplyingFilter}
            className="gap-2"
          >
            <Filter size={18} />
            Apply Filters
          </Button>
        </motion.div>

        {/* Summary Cards */}
        <motion.div
          className="mb-6 grid grid-cols-1 sm:grid-cols-2 gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
        >
          {/* Monthly Total Card */}
          <motion.div
            className="p-4 sm:p-6 bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 rounded-lg border-l-4 border-blue-500"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
          >
            <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Current Month Total</p>
            <p className="text-2xl sm:text-3xl font-bold text-blue-600 dark:text-blue-400">{formatCurrency(currentMonthSummary.monthlyTotal)}</p>
            <p className="text-gray-600 dark:text-gray-400 text-xs sm:text-sm mt-2">
              {Object.keys(currentMonthSummary.categoryBreakdown).length} categories
            </p>
          </motion.div>

          {/* Filtered Period Total Card */}
          {groupedExpenses.length > 0 && filters.timeRange !== 'all' && (
            <motion.div
              className="p-4 sm:p-6 bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30 rounded-lg border-l-4 border-red-500"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">
                {filters.timeRange === 'week' && 'Last 7 Days'}
                {filters.timeRange === 'month' && 'Last 30 Days'}
                {filters.timeRange === 'quarter' && 'Last 90 Days'}
                {filters.timeRange === 'year' && 'Last Year'}
              </p>
              <p className="text-2xl sm:text-3xl font-bold text-red-600 dark:text-red-400">{formatCurrency(totalExpenses)}</p>
              <p className="text-gray-600 dark:text-gray-400 text-xs sm:text-sm mt-2">
                {groupedExpenses.reduce((sum, [_, dayExpenses]) => sum + dayExpenses.length, 0)} transactions
              </p>
            </motion.div>
          )}

          {/* Display total expenses if no filter or all time is selected */}
          {groupedExpenses.length > 0 && filters.timeRange === 'all' && (
            <motion.div
              className="p-4 sm:p-6 bg-gradient-to-r from-red-50 to-orange-50 dark:from-red-900/30 dark:to-orange-900/30 rounded-lg border-l-4 border-red-500"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
            >
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Total Expenses (All Time)</p>
              <p className="text-2xl sm:text-3xl font-bold text-red-600 dark:text-red-400">{formatCurrency(totalExpenses)}</p>
              <p className="text-gray-600 dark:text-gray-400 text-xs sm:text-sm mt-2">
                {groupedExpenses.reduce((sum, [_, dayExpenses]) => sum + dayExpenses.length, 0)} transactions
              </p>
            </motion.div>
          )}
        </motion.div>

        {/* Expenses List - Grouped by Date */}
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
          <motion.div className="space-y-6">
            {groupedExpenses.map(([date, dayExpenses], dateIndex) => {
              // Safely calculate daily total, defaulting to 0 for any invalid amounts
              const dayTotal = dayExpenses.reduce((sum, exp) => {
                const amount = parseFloat(exp?.amount) || 0
                return sum + amount
              }, 0)
              
              const formattedDate = new Date(date).toLocaleDateString('en-US', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
              })

              return (
                <motion.div
                  key={date}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: dateIndex * 0.05 }}
                >
                  {/* Date Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900 dark:text-gray-100">{formattedDate}</h3>
                      <p className="text-sm text-gray-500 dark:text-gray-400">{dayExpenses.length} transaction(s)</p>
                    </div>
                    <p className="text-lg font-bold text-red-600 dark:text-red-400">{formatCurrency(dayTotal)}</p>
                  </div>

                  {/* Expenses for this day */}
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
                          <div className="flex items-center gap-4">
                            <div>
                              <p className="font-semibold text-gray-900 dark:text-gray-100">{expense.description}</p>
                              <p className="text-sm text-gray-500 dark:text-gray-400">
                                {CATEGORIES.find((c) => c.value === expense.category)?.label}
                              </p>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <p className="text-lg font-bold text-red-600 dark:text-red-400 min-w-24 text-right">
                            {formatCurrency(expense.amount)}
                          </p>
                          <div className="flex gap-2">
                            <motion.button
                              onClick={() => handleEdit(expense)}
                              className="p-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg text-blue-600 dark:text-blue-400"
                              whileHover={{ scale: 1.1 }}
                              whileTap={{ scale: 0.95 }}
                            >
                              <Edit2 size={18} />
                            </motion.button>
                            <motion.button
                              onClick={() => handleDelete(expense.id)}
                              className="p-2 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg text-red-600 dark:text-red-400"
                              whileHover={{ scale: 1.1 }}
                              whileTap={{ scale: 0.95 }}
                            >
                              <Trash2 size={18} />
                            </motion.button>
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

      {/* Add/Edit Expense Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          resetForm()
        }}
        title={editingId ? 'Edit Expense' : 'Add Expense'}
        className="max-w-sm"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Description"
            type="text"
            placeholder="e.g., Coffee at Starbucks"
            value={formData.description}
            onChange={(e) => {
              setFormData({ ...formData, description: e.target.value })
              setFormErrors({ ...formErrors, description: '' })
            }}
            error={formErrors.description}
          />

          <Input
            label="Amount"
            type="number"
            placeholder="0.00"
            step="0.01"
            value={formData.amount}
            onChange={(e) => {
              setFormData({ ...formData, amount: e.target.value })
              setFormErrors({ ...formErrors, amount: '' })
            }}
            error={formErrors.amount}
          />

          <Select
            label="Category"
            options={CATEGORIES}
            value={formData.category}
            onChange={(e) => {
              setFormData({ ...formData, category: e.target.value })
              setFormErrors({ ...formErrors, category: '' })
            }}
            error={formErrors.category}
          />

          <Input
            label="Date"
            type="date"
            value={formData.date}
            onChange={(e) => setFormData({ ...formData, date: e.target.value })}
          />

          <div className="flex gap-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={expensesLoading}
            >
              {editingId ? 'Update' : 'Add'} Expense
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false)
                resetForm()
              }}
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
