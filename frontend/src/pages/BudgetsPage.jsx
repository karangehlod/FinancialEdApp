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
  ProgressBar,
} from '../components/UI'
import { useBudgetStore, useExpenseStore } from '../store/index'
import { motion } from 'framer-motion'
import { Trash2, Edit2, Plus, AlertCircle, TrendingDown, PieChart } from 'lucide-react'
import { calculatePercentage } from '../utils/helpers'
import { showSuccessToast, showErrorToast } from '../utils/toast'

const CATEGORIES = [
  { value: 'FOOD', label: 'Food & Dining' },
  { value: 'TRANSPORT', label: 'Transportation' },
  { value: 'UTILITIES', label: 'Utilities' },
  { value: 'ENTERTAINMENT', label: 'Entertainment' },
  { value: 'HEALTH', label: 'Health & Fitness' },
  { value: 'EDUCATION', label: 'Education' },
  { value: 'SHOPPING', label: 'Shopping' },
  { value: 'OTHER', label: 'Other' },
]

export const BudgetsPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)
  const {
    budgets,
    alerts,
    fetchBudgets,
    fetchAlerts,
    addBudget,
    updateBudget,
    deleteBudget,
    isLoading: budgetsLoading,
  } = useBudgetStore()
  
  const { expenses = [], fetchExpenses } = useExpenseStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    month: new Date().toISOString().split('T')[0].replace(/-\d{2}$/, '-01'),
    category: 'FOOD',
    allocated_amount: '',
    recommended_amount: '',
  })
  const [formErrors, setFormErrors] = useState({})

  // Calculate current month expenses by category
  const currentMonthExpensesByCategory = useMemo(() => {
    const today = new Date()
    const currentMonth = today.getMonth()
    const currentYear = today.getFullYear()

    const categoryExpenses = {}
    ;(expenses || []).forEach((expense) => {
      const expenseDate = new Date(expense?.date)
      if (!isNaN(expenseDate) && 
          expenseDate.getMonth() === currentMonth && 
          expenseDate.getFullYear() === currentYear) {
        // Normalize category to UPPERCASE to match budget categories
        const category = (expense?.category || 'OTHER').toUpperCase()
        categoryExpenses[category] = (categoryExpenses[category] || 0) + (parseFloat(expense?.amount) || 0)
      }
    })
    return categoryExpenses
  }, [expenses])

  // Fetch data only once when authenticated
  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchBudgets()
      fetchAlerts()
      fetchExpenses()
    }
  }, [isAuthenticated])

  const validateForm = () => {
    const errors = {}
    if (!formData.month) errors.month = 'Month is required'
    if (!formData.category) errors.category = 'Category is required'
    if (!formData.allocated_amount) errors.allocated_amount = 'Budget limit is required'
    else if (parseFloat(formData.allocated_amount) <= 0) errors.allocated_amount = 'Budget must be positive'
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
      const data = {
        month: formData.month,
        category: formData.category,
        allocated_amount: parseFloat(formData.allocated_amount),
        recommended_amount: formData.recommended_amount ? parseFloat(formData.recommended_amount) : undefined,
      }

      if (editingId) {
        await updateBudget(editingId, data)
        showSuccessToast('Budget updated successfully')
      } else {
        await addBudget(data)
        showSuccessToast('Budget created successfully')
      }
      setIsModalOpen(false)
      resetForm()
      fetchAlerts()
    } catch (err) {
      showErrorToast(editingId ? 'Failed to update budget' : 'Failed to create budget')
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this budget?')) {
      try {
        // logger.info('Deleting budget', { id })
        await deleteBudget(id)
        // logger.info('Budget deleted successfully', { id })
        showSuccessToast('Budget deleted successfully')
      } catch (err) {
        console.error('❌ Delete error:', err)
        showErrorToast(`Failed to delete budget: ${err?.message || 'Unknown error'}`)
      }
    }
  }

  const handleEdit = (budget) => {
    setEditingId(budget.id)
    setFormData({
      month: budget.month,
      category: budget.category,
      allocated_amount: budget.allocated_amount.toString(),
      recommended_amount: budget.recommended_amount ? budget.recommended_amount.toString() : '',
    })
    setIsModalOpen(true)
  }

  const resetForm = () => {
    setFormData({
      month: new Date().toISOString().split('T')[0].replace(/-\d{2}$/, '-01'),
      category: 'FOOD',
      allocated_amount: '',
      recommended_amount: '',
    })
    setFormErrors({})
    setEditingId(null)
  }

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="" style={{ maxWidth: 'var(--content-max-width)' }}>
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageContainer
        title="Budgets"
        subtitle="Set and monitor your spending limits"
        icon={PieChart}
        iconSize={'var(--page-icon-size)'}
        iconAlt="Budgets"

        action={
          <Button
            onClick={() => {
              resetForm()
              setIsModalOpen(true)
            }}
            variant="primary"
            className="gap-2 w-full sm:w-auto text-xs sm:text-sm py-2 sm:py-3 px-3 sm:px-4"
          >
            <Plus size={18} className="sm:w-5 sm:h-5" />
            <span className="hidden xs:inline">New Budget</span>
            <span className="xs:hidden">Add</span>
          </Button>
        }
      >
        {/* Alerts */}
        {alerts && alerts.length > 0 && (
          <motion.div
            className="mb-6 space-y-2 sm:space-y-3"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3 sm:p-4 bg-yellow-50 dark:bg-yellow-900/20 border-l-4 border-yellow-400 dark:border-yellow-600 rounded flex items-start gap-2 sm:gap-3 text-xs sm:text-sm"
              >
                <AlertCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-yellow-600 dark:text-yellow-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-yellow-800 dark:text-yellow-300">{alert.message}</p>
                  <p className="text-xs sm:text-sm text-yellow-700 dark:text-yellow-400 break-words">{alert.description}</p>
                </div>
              </div>
            ))}
          </motion.div>
        )}

        {/* Current Month Spending Recommendations */}
        {Object.keys(currentMonthExpensesByCategory).length > 0 && budgets.length === 0 && (
          <motion.div
            className="mb-6 p-3 sm:p-4 md:p-6 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="flex items-start gap-2 sm:gap-3 mb-4">
              <TrendingDown style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-semibold text-blue-900 dark:text-blue-300 text-sm sm:text-base">Create Budgets Based on Your Spending</h3>
                <p className="text-xs sm:text-sm text-blue-700 dark:text-blue-400 mt-1">
                  We detected spending in {Object.keys(currentMonthExpensesByCategory).length} categories this month. 
                  Create budgets to track and control your spending.
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 xs:grid-cols-2 sm:grid-cols-2 lg:grid-cols-3 gap-2 sm:gap-3">
              {Object.entries(currentMonthExpensesByCategory).map(([category, spent]) => {
                const categoryLabel = CATEGORIES.find(c => c.value === category)?.label || category
                const recommendedBudget = Math.ceil(spent * 1.2) // Recommend 20% more than spent
                return (
                  <motion.div
                    key={category}
                    className="p-3 bg-white dark:bg-gray-800 rounded border border-blue-200 dark:border-blue-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 text-xs sm:text-sm"
                    whileHover={{ y: -2 }}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-gray-900 dark:text-gray-100 truncate">{categoryLabel}</p>
                      <p className="text-xs text-gray-600 dark:text-gray-400">Spent: {formatCurrency(spent)}</p>
                    </div>
                    <Button
                      onClick={() => {
                        setFormData({
                          month: new Date().toISOString().split('T')[0].replace(/-\d{2}$/, '-01'),
                          category,
                          allocated_amount: recommendedBudget.toString(),
                          recommended_amount: spent.toString(),
                        })
                        setIsModalOpen(true)
                      }}
                      variant="secondary"
                      className="text-xs px-2 py-1 flex-shrink-0 w-full sm:w-auto"
                    >
                      Set Budget
                    </Button>
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        )}

        {/* Budgets Grid */}
        {budgetsLoading ? (
          <div className="flex items-center justify-center min-h-96">
            <LoadingSpinner size="lg" />
          </div>
        ) : budgets.length === 0 ? (
          <EmptyState
            icon={Plus}
            title="No budgets yet"
            description="Create a budget to manage your spending"
            action={
              <Button onClick={() => setIsModalOpen(true)} variant="primary">
                Create First Budget
              </Button>
            }
          />
        ) : (
          <motion.div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 sm:gap-4 md:gap-6 w-full">
            {budgets.map((budget, index) => {
              // Real-time calculation: always use current month expenses
              const currentMonthSpending = currentMonthExpensesByCategory[budget.category] || 0
              const remainingBudget = Math.max(0, budget.allocated_amount - currentMonthSpending)
              const isOverBudget = currentMonthSpending > budget.allocated_amount
              const percentage = calculatePercentage(currentMonthSpending, budget.allocated_amount)
              const isAlertTriggered = percentage >= 80

              return (
                <motion.div
                  key={budget.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="h-full"
                >
                  <Card className={`h-full flex flex-col text-xs sm:text-sm ${isAlertTriggered || isOverBudget ? 'border-l-4 border-yellow-500' : 'border-l-4 border-green-500'}`}>
                    {/* Budget Header */}
                    <div className="flex items-start justify-between mb-4 gap-2 flex-wrap">
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base sm:text-lg font-bold text-gray-900 dark:text-gray-100 break-words">
                          {CATEGORIES.find((c) => c.value === budget.category)?.label}
                        </h3>
                        <p className="text-xs sm:text-sm text-gray-500 dark:text-gray-400 mt-1">
                          <span className="font-semibold">{formatCurrency(currentMonthSpending)}</span>
                          <span className="text-gray-400"> / </span>
                          <span className="font-semibold">{formatCurrency(budget.allocated_amount)}</span>
                        </p>
                      </div>
                      <div className="flex gap-1 sm:gap-2 flex-shrink-0">
                        <motion.button
                          onClick={() => handleEdit(budget)}
                          className="p-2 hover:bg-blue-50 rounded-lg text-blue-600 transition-colors"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          title="Edit"
                          aria-label="Edit budget"
                        >
                          <Edit2 size={16} className="sm:w-5 sm:h-5" />
                        </motion.button>
                        <motion.button
                          onClick={() => handleDelete(budget.id)}
                          className="p-2 hover:bg-red-50 rounded-lg text-red-600 transition-colors"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                          title="Delete"
                          aria-label="Delete budget"
                        >
                          <Trash2 size={16} className="sm:w-5 sm:h-5" />
                        </motion.button>
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="mb-4">
                      <ProgressBar
                        value={currentMonthSpending}
                        max={budget.allocated_amount}
                        color={isOverBudget ? 'red' : isAlertTriggered ? 'yellow' : 'primary'}
                        showLabel={false}
                      />
                    </div>

                    {/* Budget Stats */}
                    <div className="flex flex-col gap-3 mt-auto pt-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                            <span className="font-semibold">{Math.min(Math.round(percentage), 100)}%</span>
                            <span className="ml-1">used</span>
                          </p>
                        </div>
                        {isAlertTriggered && !isOverBudget && (
                          <Badge variant="warning" className="text-xs flex-shrink-0">
                            Alert
                          </Badge>
                        )}
                        {isOverBudget && (
                          <Badge variant="danger" className="text-xs flex-shrink-0">
                            Over Budget
                          </Badge>
                        )}
                      </div>
                      
                      {/* Remaining Budget */}
                      <div className={`p-2 rounded ${isOverBudget ? 'bg-red-50 dark:bg-red-900/20' : 'bg-green-50 dark:bg-green-900/20'}`}>
                        <p className={`text-xs font-semibold ${isOverBudget ? 'text-red-700 dark:text-red-400' : 'text-green-700 dark:text-green-400'}`}>
                          {isOverBudget ? 'Over Budget by' : 'Remaining Budget'}
                        </p>
                        <p className={`text-sm font-bold ${isOverBudget ? 'text-red-600' : 'text-green-600'}`}>
                          {isOverBudget 
                            ? formatCurrency(currentMonthSpending - budget.allocated_amount) 
                            : formatCurrency(remainingBudget)}
                        </p>
                      </div>
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </PageContainer>

      {/* Add/Edit Budget Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          resetForm()
        }}
        title={editingId ? 'Edit Budget' : 'Create Budget'}
        className=""
      >
        <form onSubmit={handleSubmit} className="space-y-3 sm:space-y-4">
          <Input
            label="Month"
            type="date"
            value={formData.month}
            onChange={(e) => {
              setFormData({ ...formData, month: e.target.value })
              setFormErrors({ ...formErrors, month: '' })
            }}
            error={formErrors.month}
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
            label="Budget Limit"
            type="number"
            placeholder="1000.00"
            step="0.01"
            value={formData.allocated_amount}
            onChange={(e) => {
              setFormData({ ...formData, allocated_amount: e.target.value })
              setFormErrors({ ...formErrors, allocated_amount: '' })
            }}
            error={formErrors.allocated_amount}
          />

          <Input
            label="Recommended Amount (Optional)"
            type="number"
            placeholder="800.00"
            step="0.01"
            value={formData.recommended_amount}
            onChange={(e) => setFormData({ ...formData, recommended_amount: e.target.value })}
          />

          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 pt-2 sm:pt-4">
            <Button
              type="submit"
              variant="primary"
              className="flex-1 text-xs sm:text-sm py-2 sm:py-3"
              isLoading={budgetsLoading}
            >
              {editingId ? 'Update' : 'Create'} Budget
            </Button>
            <Button
              type="button"
              variant="secondary"
              className="flex-1 text-xs sm:text-sm py-2 sm:py-3"
              onClick={() => {
                setIsModalOpen(false)
                resetForm()
              }}
            >
              Cancel
            </Button>
          </div>
        </form>
      </Modal>
    </Layout>
  )
}
