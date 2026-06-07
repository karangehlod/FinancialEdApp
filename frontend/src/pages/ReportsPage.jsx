import React, { useEffect, useState } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import { Card, Button, StatCard, LoadingSpinner, EmptyState, Alert } from '../components/UI'
import {
  useExpenseStore,
  useBudgetStore,
  useGoalStore,
  useLoanStore,
} from '../store/index'
import { motion } from 'framer-motion'
import {
  BarChart3,
  PieChart as PieChartIcon,
  Download,
  Filter,
  Calendar,
} from 'lucide-react'
import { formatDate } from '../utils/helpers'
import { showSuccessToast, showErrorToast } from '../utils/toast'
import { exportService } from '../services/apiService'

export const ReportsPage = () => {
  const { isAuthenticated, isLoading: authLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const { expenses, fetchExpenses, isLoading: expensesLoading } = useExpenseStore()
  const { budgets, fetchBudgets, isLoading: budgetsLoading } = useBudgetStore()
  const { goals, fetchGoals, isLoading: goalsLoading } = useGoalStore()
  const { loans, fetchLoans, isLoading: loansLoading } = useLoanStore()

  const [activeTab, setActiveTab] = useState('overview')
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [isExporting, setIsExporting] = useState(false)
  const [isApplyingFilters, setIsApplyingFilters] = useState(false)

  // Fetch data on component mount
  useEffect(() => {
    if (isAuthenticated) {
      try {
        // Explicitly fetch all data to ensure backend calls are made
        fetchExpenses()
        fetchBudgets()
        fetchGoals()
        fetchLoans()
      } catch (error) {
        console.error('Error loading reports data:', error)
      }
    }
  }, [isAuthenticated, fetchExpenses, fetchBudgets, fetchGoals, fetchLoans])

  // ===== REAL-TIME UPDATES - Refetch when page focus returns =====
  useEffect(() => {
    const handlePageFocus = () => {
      try {
        // logger.info('Reports page focused - refetching data for real-time updates')
        fetchExpenses()
        fetchBudgets()
        fetchGoals()
        fetchLoans()
      } catch (error) {
        console.error('Error refetching reports data:', error)
      }
    }

    // Listen for page visibility changes (user returns to tab)
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        handlePageFocus()
      }
    })

    // Cleanup
    return () => {
      document.removeEventListener('visibilitychange', handlePageFocus)
    }
  }, [fetchExpenses, fetchBudgets, fetchGoals, fetchLoans])

  const isLoadingData = expensesLoading || budgetsLoading || goalsLoading || loansLoading

  // Handle applying date range filters
  const handleApplyDateFilter = async () => {
    setIsApplyingFilters(true)
    try {
      // Fetch expenses with date filters if date range is set
      const filters = {}
      if (dateRange.start) filters.start_date = dateRange.start
      if (dateRange.end) filters.end_date = dateRange.end
      
      await fetchExpenses(filters)
      showSuccessToast('Report updated with selected date range')
    } catch (error) {
      console.error('Error applying filters:', error)
      showErrorToast('Failed to apply filters')
    } finally {
      setIsApplyingFilters(false)
    }
  }

  // Calculate report statistics with safe defaults
  const stats = React.useMemo(() => {
    const safeExpenses = Array.isArray(expenses) ? expenses : []
    const safeBudgets = Array.isArray(budgets) ? budgets : []
    const safeGoals = Array.isArray(goals) ? goals : []
    const safeLoans = Array.isArray(loans) ? loans : []

    const totalExpenses = safeExpenses.reduce((sum, e) => {
      const amount = parseFloat(e?.amount) || 0
      return sum + (isNaN(amount) ? 0 : amount)
    }, 0)
    
    const totalBudgeted = safeBudgets.reduce((sum, b) => {
      const allocated = parseFloat(b?.allocated_amount) || 0
      return sum + (isNaN(allocated) ? 0 : allocated)
    }, 0)
    
    const goalProgress = safeGoals.reduce((sum, g) => {
      const current = parseFloat(g?.current_amount) || 0
      return sum + (isNaN(current) ? 0 : current)
    }, 0)
    
    const totalLoans = safeLoans.reduce((sum, l) => {
      const amount = parseFloat(l?.amount) || 0
      return sum + (isNaN(amount) ? 0 : amount)
    }, 0)

    const budgetUtilization = totalBudgeted > 0 ? (totalExpenses / totalBudgeted) * 100 : 0

    return {
      totalExpenses: isNaN(totalExpenses) ? 0 : totalExpenses,
      totalBudgeted: isNaN(totalBudgeted) ? 0 : totalBudgeted,
      goalProgress: isNaN(goalProgress) ? 0 : goalProgress,
      totalLoans: isNaN(totalLoans) ? 0 : totalLoans,
      budgetUtilization: isNaN(budgetUtilization) ? 0 : budgetUtilization,
      expenseCount: safeExpenses.length,
      budgetCount: safeBudgets.length,
      goalCount: safeGoals.length,
      loanCount: safeLoans.length,
    }
  }, [expenses, budgets, goals, loans])

  // Group expenses by category with safe calculations
  const expensesByCategory = React.useMemo(() => {
    const grouped = {}
    const safeExpenses = Array.isArray(expenses) ? expenses : []
    
    safeExpenses.forEach((expense) => {
      const category = expense?.category || 'Uncategorized'
      if (!grouped[category]) {
        grouped[category] = { amount: 0, count: 0 }
      }
      const amount = parseFloat(expense?.amount) || 0
      grouped[category].amount += isNaN(amount) ? 0 : amount
      grouped[category].count += 1
    })
    return grouped
  }, [expenses])

  // Group expenses by month with safe calculations
  const expensesByMonth = React.useMemo(() => {
    const grouped = {}
    const safeExpenses = Array.isArray(expenses) ? expenses : []
    
    safeExpenses.forEach((expense) => {
      const date = expense?.date ? new Date(expense.date) : new Date()
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
      if (!grouped[monthKey]) {
        grouped[monthKey] = { amount: 0, count: 0 }
      }
      const amount = parseFloat(expense?.amount) || 0
      grouped[monthKey].amount += isNaN(amount) ? 0 : amount
      grouped[monthKey].count += 1
    })
    
    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .reverse()
      .slice(0, 12)
  }, [expenses])

  // Get current month expenses by category (for budget report)
  const currentMonthExpensesByCategory = React.useMemo(() => {
    const grouped = {}
    const today = new Date()
    const currentMonth = today.getMonth()
    const currentYear = today.getFullYear()
    
    const safeExpenses = Array.isArray(expenses) ? expenses : []
    
    safeExpenses.forEach((expense) => {
      const expenseDate = new Date(expense?.date)
      // Only include current month expenses
      if (!isNaN(expenseDate) && 
          expenseDate.getMonth() === currentMonth && 
          expenseDate.getFullYear() === currentYear) {
        
        const category = (expense?.category || 'Other').toLowerCase().trim()
        if (!grouped[category]) {
          grouped[category] = { amount: 0, count: 0 }
        }
        const amount = parseFloat(expense?.amount) || 0
        grouped[category].amount += isNaN(amount) ? 0 : amount
        grouped[category].count += 1
      }
    })
    
    return grouped
  }, [expenses])

  const handleExport = async (format) => {
    try {
      setIsExporting(true)
      const filters = {}
      if (dateRange.start) filters.start_date = dateRange.start
      if (dateRange.end) filters.end_date = dateRange.end

      const blob = await exportService.exportReport(format, filters)
      
      if (!blob || blob.size === 0) {
        throw new Error('Export returned empty data')
      }
      
      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      
      // Determine file extension and name
      const fileExtension = format === 'excel' ? 'xlsx' : format
      const timestamp = new Date().toISOString().split('T')[0]
      link.download = `financial-report-${timestamp}.${fileExtension}`
      
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      showSuccessToast(`Report exported as ${format.toUpperCase()}`)
    } catch (error) {
      console.error('Export error:', error)
      showErrorToast(`Failed to export report: ${error.message}`)
    } finally {
      setIsExporting(false)
    }
  }

  if (authLoading || isLoadingData) {
    return (
      <Layout>
        <PageContainer>
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        </PageContainer>
      </Layout>
    )
  }

  const tabOptions = [
    { id: 'overview', label: 'Overview', icon: BarChart3 },
    { id: 'expenses', label: 'Expenses Analysis', icon: PieChartIcon },
    { id: 'budgets', label: 'Budget Report', icon: BarChart3 },
    { id: 'debts', label: 'Debts & Loans', icon: BarChart3 },
  ]

  return (
    <Layout>
      <PageContainer
        title="Financial Reports"
        subtitle="Analyze your financial data and track progress"
        icon={BarChart3}
        iconSize={'var(--page-icon-size)'}
        iconAlt="Reports"
        action={
          <div className="flex gap-3">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isExporting}
              icon={Download}
            >
              {isExporting ? 'Exporting...' : 'Export CSV'}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('excel')}
              disabled={isExporting}
              icon={Download}
            >
              {isExporting ? 'Exporting...' : 'Export Excel'}
            </Button>
          </div>
        }
      >
        {/* Date Range Filter */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-8"
        >
          <Card className="p-6">
            <div className="flex items-center gap-4">
              <Calendar style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-primary-600 dark:text-primary-400" />
              <div className="flex gap-4 flex-1 items-center">
                <input
                  type="date"
                  value={dateRange.start}
                  onChange={(e) => setDateRange({ ...dateRange, start: e.target.value })}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <span className="text-gray-400 dark:text-gray-500">to</span>
                <input
                  type="date"
                  value={dateRange.end}
                  onChange={(e) => setDateRange({ ...dateRange, end: e.target.value })}
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <Button
                  onClick={handleApplyDateFilter}
                  disabled={isApplyingFilters || (!dateRange.start && !dateRange.end)}
                  isLoading={isApplyingFilters}
                  icon={Filter}
                >
                  {isApplyingFilters ? 'Applying...' : 'Apply'}
                </Button>
              </div>
            </div>
          </Card>
        </motion.div>

        {/* Key Statistics */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8"
        >
          <StatCard
            title="Total Expenses"
            value={formatCurrency(stats.totalExpenses)}
            change={`${stats.expenseCount} transactions`}
            icon={BarChart3}
            color="red"
          />
          <StatCard
            title="Total Budgeted"
            value={formatCurrency(stats.totalBudgeted)}
            change={`${stats.budgetCount} budgets`}
            icon={BarChart3}
            color="blue"
          />
          <StatCard
            title="Budget Utilization"
            value={`${Math.round(stats.budgetUtilization)}%`}
            change={stats.budgetUtilization > 100 ? 'Over budget' : 'On track'}
            icon={PieChartIcon}
            color={stats.budgetUtilization > 100 ? 'red' : 'green'}
          />
          <StatCard
            title="Goal Progress"
            value={formatCurrency(stats.goalProgress)}
            change={`${stats.goalCount} goals`}
            icon={BarChart3}
            color="purple"
          />
        </motion.div>

        {/* Tabs */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex gap-2 mb-8 overflow-x-auto pb-2 border-b border-gray-200 dark:border-gray-700">
            {tabOptions.map((option) => (
              <button
                key={option.id}
                onClick={() => setActiveTab(option.id)}
                className={`px-6 py-3 font-medium whitespace-nowrap transition-all border-b-2 ${
                  activeTab === option.id
                    ? 'border-blue-600 text-blue-600 dark:text-blue-400'
                    : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
                }`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {/* Tab Contents */}
          <div className="mt-8">
            {activeTab === 'overview' && (
              <div className="space-y-6">
                <Card className="p-6">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Summary</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Income (Estimated)</p>
                      <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                        {formatCurrency(stats.totalBudgeted)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Spending</p>
                      <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                        {formatCurrency(stats.totalExpenses)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Remaining Budget</p>
                      <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        {formatCurrency(Math.max(0, stats.totalBudgeted - stats.totalExpenses))}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Debt (Loans)</p>
                      <p className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                        {formatCurrency(stats.totalLoans)}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>
            )}

            {activeTab === 'expenses' && (
              <div className="space-y-6">
                <Card className="p-6">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Recent Transactions</h3>
                  {expenses && expenses.length > 0 ? (
                    <div className="space-y-4" style={{ maxHeight: 'var(--placeholder-height)', overflowY: 'auto' }}>
                      {[...expenses]
                        .sort((a, b) => new Date(b.date) - new Date(a.date))
                        .slice(0, 50)
                        .map((expense) => (
                          <div key={expense.id} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                            <div>
                              <p className="font-medium text-gray-900 dark:text-gray-100">{expense.description}</p>
                              <p className="text-sm text-gray-600 dark:text-gray-400">{formatDate(expense.date)}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(expense.amount)}</p>
                              <p className="text-xs text-gray-600 dark:text-gray-400">{expense.category}</p>
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <EmptyState message="No expense data available. Make sure data is loaded from backend." />
                  )}
                </Card>

                <Card className="p-6">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Expenses by Category</h3>
                  {Object.keys(expensesByCategory).length > 0 ? (
                    <div className="space-y-4">
                      {Object.entries(expensesByCategory)
                        .sort(([, a], [, b]) => b.amount - a.amount)
                        .map(([category, { amount, count }]) => {
                          const percentage = stats.totalExpenses > 0 
                            ? ((amount / stats.totalExpenses) * 100).toFixed(1)
                            : '0'
                          return (
                            <div key={category} className="flex items-center justify-between">
                              <div>
                                <p className="font-medium text-gray-900 dark:text-gray-100">{category}</p>
                                <p className="text-sm text-gray-600 dark:text-gray-400">{count} transactions</p>
                              </div>
                              <div className="text-right">
                                <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(amount)}</p>
                                <p className="text-sm text-gray-600 dark:text-gray-400">{percentage}%</p>
                              </div>
                            </div>
                          )
                        })}
                    </div>
                  ) : (
                    <EmptyState message="No expense data available" />
                  )}
                </Card>

                <Card className="p-6">
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-6">Monthly Trend</h3>
                  {expensesByMonth.length > 0 ? (
                    <div className="space-y-4">
                      {expensesByMonth.map(([month, { amount, count }]) => (
                        <div key={month} className="flex items-center justify-between">
                          <div>
                            <p className="font-medium text-gray-900 dark:text-gray-100">{month}</p>
                            <p className="text-sm text-gray-600 dark:text-gray-400">{count} transactions</p>
                          </div>
                          <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(amount)}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyState message="No monthly data available" />
                  )}
                </Card>
              </div>
            )}

            {activeTab === 'budgets' && (
              <Card className="p-6">
                <h3 className="text-xl font-semibold text-gray-900 dark:text-gray-100 mb-2">Budget Status - Current Month</h3>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-6">Showing budgets and expenses for {new Date().toLocaleString('default', { month: 'long', year: 'numeric' })}</p>
                {budgets && budgets.length > 0 ? (
                  <div className="space-y-6">
                    {(() => {
                      // Filter to current month budgets
                      const today = new Date()
                      const currentMonth = today.getMonth()
                      const currentYear = today.getFullYear()
                      const monthKey = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`
                      
                      const currentMonthBudgets = budgets.filter(b => {
                        if (!b?.month) return false
                        const budgetMonthStr = typeof b.month === 'string' 
                          ? b.month.substring(0, 7)
                          : new Date(b.month).toISOString().substring(0, 7)
                        return budgetMonthStr === monthKey
                      })

                      return currentMonthBudgets.length > 0 ? (
                        currentMonthBudgets.map((budget) => {
                          // Get expenses for this category in current month
                          const categoryKey = (budget?.category || 'Other').toLowerCase().trim()
                          const categoryExpenses = currentMonthExpensesByCategory[categoryKey]?.amount || 0
                          
                          // Use allocated_amount field (correct backend field)
                          const allocated = parseFloat(budget?.allocated_amount) || 0
                          const utilization = allocated > 0 ? (categoryExpenses / allocated) * 100 : 0
                          const safeUtilization = isNaN(utilization) ? 0 : utilization
                          
                          return (
                            <div key={budget?.id}>
                              <div className="flex items-center justify-between mb-3">
                                <div>
                                  <p className="font-medium text-gray-900 dark:text-gray-100 capitalize">{budget?.category || 'N/A'}</p>
                                  <p className="text-xs text-gray-600 dark:text-gray-400">{currentMonthExpensesByCategory[categoryKey]?.count || 0} transactions</p>
                                </div>
                                <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                                  {formatCurrency(categoryExpenses)} / {formatCurrency(allocated)}
                                </p>
                              </div>
                              <div className="w-full h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                                <motion.div
                                  className={`h-full ${
                                    safeUtilization > 100 
                                      ? 'bg-red-600' 
                                      : safeUtilization > 90 
                                      ? 'bg-yellow-600' 
                                      : 'bg-green-600'
                                  }`}
                                  initial={{ width: 0 }}
                                  animate={{ width: `${Math.min(safeUtilization, 100)}%` }}
                                  transition={{ duration: 0.6, ease: 'easeOut' }}
                                />
                              </div>
                              <div className="flex justify-between items-center mt-2">
                                <p className="text-xs text-gray-600 dark:text-gray-400">{safeUtilization.toFixed(1)}% used</p>
                                <p className="text-xs font-medium text-gray-700 dark:text-gray-300">
                                  Remaining: {formatCurrency(Math.max(0, allocated - categoryExpenses))}
                                </p>
                              </div>
                            </div>
                          )
                        })
                      ) : (
                        <EmptyState message="No budgets created for this month. Create a budget to track your spending." />
                      )
                    })()}
                  </div>
                ) : (
                  <EmptyState message="No budgets created yet. Start creating budgets to track your spending." />
                )}
              </Card>
            )}

            {activeTab === 'debts' && (
              <Card className="p-6">
                <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-6">Debts & Loans Report</h2>
                
                {loans && loans.length > 0 ? (
                  <div className="space-y-6">
                    {/* Summary Cards */}
                    <motion.div
                      className="grid grid-cols-1 md:grid-cols-3 gap-4"
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                    >
                      <Card className="bg-blue-50 dark:bg-blue-900/20 p-4">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Loan Amount</p>
                        <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                          {formatCurrency(
                            loans.reduce((sum, l) => sum + (parseFloat(l?.principal_amount) || parseFloat(l?.amount) || 0), 0)
                          )}
                        </p>
                      </Card>
                      
                      <Card className="bg-yellow-50 dark:bg-yellow-900/20 p-4">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Monthly EMI</p>
                        <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
                          {formatCurrency(
                            loans.reduce((sum, l) => sum + (parseFloat(l?.emi_amount) || 0), 0)
                          )}
                        </p>
                      </Card>
                      
                      <Card className="bg-red-50 dark:bg-red-900/20 p-4">
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Number of Loans</p>
                        <p className="text-2xl font-bold text-red-600 dark:text-red-400">{loans.length}</p>
                      </Card>
                    </motion.div>

                    {/* Detailed Loan Table */}
                    <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                      <div className="px-6 py-4 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Loan Details</h3>
                      </div>
                      
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead className="bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
                            <tr>
                              <th className="px-6 py-3 text-left font-semibold text-gray-900 dark:text-gray-100">Lender</th>
                              <th className="px-6 py-3 text-left font-semibold text-gray-900 dark:text-gray-100">Type</th>
                              <th className="px-6 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">Principal</th>
                              {/* Less important columns hidden on xs to avoid horizontal overflow */}
                              <th className="hidden sm:table-cell px-6 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">Interest Rate</th>
                              <th className="hidden sm:table-cell px-6 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">Monthly EMI</th>
                              <th className="hidden sm:table-cell px-6 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">Outstanding</th>
                              <th className="hidden sm:table-cell px-6 py-3 text-right font-semibold text-gray-900 dark:text-gray-100">Remaining Months</th>
                            </tr>
                          </thead>
                          <tbody>
                            {loans.map((loan, index) => {
                              const principal = parseFloat(loan?.principal_amount) || parseFloat(loan?.amount) || 0
                              const emi = parseFloat(loan?.emi_amount) || 0
                              const outstanding = parseFloat(loan?.outstanding_balance) || principal
                              const remainingMonths = loan?.loan_term_months || loan?.term_months || 0
                              
                              return (
                                <tr key={loan?.id || index} className="border-b border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                  <td className="px-6 py-3 text-gray-900 dark:text-gray-100 font-medium">{loan?.lender_name || loan?.lender || 'N/A'}</td>
                                  <td className="px-6 py-3 text-gray-600 dark:text-gray-400 capitalize">{loan?.loan_type || 'N/A'}</td>
                                  <td className="px-6 py-3 text-right text-gray-900 dark:text-gray-100 font-medium whitespace-nowrap">{formatCurrency(principal)}</td>
                                  <td className="hidden sm:table-cell px-6 py-3 text-right text-gray-900 dark:text-gray-100 whitespace-nowrap">{parseFloat(loan?.interest_rate || 0).toFixed(2)}%</td>
                                  <td className="hidden sm:table-cell px-6 py-3 text-right text-gray-900 dark:text-gray-100 font-medium whitespace-nowrap">{formatCurrency(emi)}</td>
                                  <td className="hidden sm:table-cell px-6 py-3 text-right text-gray-900 dark:text-gray-100 whitespace-nowrap">{formatCurrency(outstanding)}</td>
                                  <td className="hidden sm:table-cell px-6 py-3 text-right whitespace-nowrap">
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                                       remainingMonths > 12 
                                         ? 'bg-red-100 text-red-800'
                                         : remainingMonths > 6
                                         ? 'bg-yellow-100 text-yellow-800'
                                         : 'bg-green-100 text-green-800'
                                     }`}>
                                      {remainingMonths} months
                                     </span>
                                   </td>
                                </tr>
                              )
                            })}
                          </tbody>
                        </table>
                      </div>
                    </div>

                    {/* Debt-to-Income Analysis */}
                    <Card className="p-6 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-900/10">
                      <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Debt Analysis</h3>
                      <div className="space-y-4">
                        <div>
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total EMI Commitment</p>
                          <p className="text-xl font-bold text-purple-600 dark:text-purple-400">
                            {formatCurrency(loans.reduce((sum, l) => sum + (parseFloat(l?.emi_amount) || 0), 0))} / month
                          </p>
                          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">This is your fixed monthly loan payment obligation</p>
                        </div>
                        <div className="border-t border-purple-200 dark:border-purple-800 pt-4">
                          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Interest Rate Range</p>
                          <p className="text-lg font-medium text-gray-900 dark:text-gray-100">
                            {Math.min(...loans.map(l => parseFloat(l?.interest_rate || 0)), 0).toFixed(2)}% - {Math.max(...loans.map(l => parseFloat(l?.interest_rate || 0)), 0).toFixed(2)}%
                          </p>
                        </div>
                      </div>
                    </Card>
                  </div>
                ) : (
                  <EmptyState 
                    title="No Loans Found"
                    description="You don't have any loans registered. Add loans to track your debt obligations."
                  />
                )}
              </Card>
            )}
          </div>
        </motion.div>
      </PageContainer>
    </Layout>
  )
}
