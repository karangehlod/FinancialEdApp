import React from 'react'
import { Card, Button } from '../UI'
import { motion } from 'framer-motion'
import { ArrowRight } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'
import { exportService } from '../../services/exportService'
import { showSuccessToast } from '../../utils/toast'

export const ReportsTab = ({ expenses = [], budgets = [], goals = [], loans = [] }) => {
  // Calculate summary statistics
  const totalExpenses = expenses.reduce((sum, e) => sum + (parseFloat(e?.amount) || 0), 0)
  const totalBudgets = budgets.reduce((sum, b) => sum + (parseFloat(b?.amount) || 0), 0)
  const totalSpentOnBudgets = budgets.reduce((sum, b) => sum + (parseFloat(b?.spent) || 0), 0)
  const activeGoals = goals.filter(g => !g?.completed).length

  const handleExport = (exportFunction, data, successMessage) => {
    try {
      const success = exportFunction(data)
      if (success) {
        showSuccessToast(successMessage)
      }
    } catch (error) {
      console.error('Export error:', error)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      {/* Summary Cards */}
      <Card className="mb-8">
        <h3 className="text-lg font-bold mb-6 dark:text-gray-100">Financial Reports Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="p-4 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Income (This Month)</p>
            <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">$0.00</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">No income data available</p>
          </div>
          <div className="p-4 bg-red-50 dark:bg-red-900/30 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Total Expenses</p>
            <p className="text-3xl font-bold text-red-600 dark:text-red-400">{formatCurrency(totalExpenses)}</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">{expenses.length} transactions</p>
          </div>
          <div className="p-4 bg-green-50 dark:bg-green-900/30 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Budget Remaining</p>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400">
              {formatCurrency(Math.max(0, totalBudgets - totalSpentOnBudgets))}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">Out of {formatCurrency(totalBudgets)}</p>
          </div>
          <div className="p-4 bg-purple-50 dark:bg-purple-900/30 rounded-lg">
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">Savings Goal Progress</p>
            <p className="text-3xl font-bold text-purple-600 dark:text-purple-400">{activeGoals}</p>
            <p className="text-xs text-gray-500 dark:text-gray-500 mt-2">Goals in progress</p>
          </div>
        </div>
      </Card>

      {/* Export Section */}
      <Card>
        <h3 className="text-lg font-bold mb-6 dark:text-gray-100">Export Data</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <Button
            variant="secondary"
            className="flex items-center justify-center gap-2"
            onClick={() => handleExport(
              exportService.exportExpensesCSV,
              expenses,
              'Expenses exported as CSV'
            )}
          >
            <ArrowRight size={18} />
            Expenses CSV
          </Button>
          <Button
            variant="secondary"
            className="flex items-center justify-center gap-2"
            onClick={() => handleExport(
              exportService.exportBudgetsCSV,
              budgets,
              'Budgets exported as CSV'
            )}
          >
            <ArrowRight size={18} />
            Budgets CSV
          </Button>
          <Button
            variant="secondary"
            className="flex items-center justify-center gap-2"
            onClick={() => handleExport(
              exportService.exportGoalsCSV,
              goals,
              'Goals exported as CSV'
            )}
          >
            <ArrowRight size={18} />
            Goals CSV
          </Button>
          <Button
            variant="secondary"
            className="flex items-center justify-center gap-2"
            onClick={() => handleExport(
              (data) => exportService.exportDashboardSummary({
                totalExpenses,
                totalBudgets,
                totalSpentOnBudgets,
                activeGoals
              }, expenses, budgets, goals),
              null,
              'Dashboard summary exported as JSON'
            )}
          >
            <ArrowRight size={18} />
            Summary JSON
          </Button>
        </div>
      </Card>
    </motion.div>
  )
}
