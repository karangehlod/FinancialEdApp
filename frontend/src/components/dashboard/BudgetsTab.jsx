import React, { useMemo } from 'react'
import { Card, EmptyState, Button } from '../UI'
import { motion } from 'framer-motion'
import { Wallet, AlertCircle } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'
import { useNavigate } from 'react-router-dom'
import { DashboardDataService } from './DashboardDataService'

export const BudgetsTab = ({ budgets = [], expenses = [] }) => {
  const navigate = useNavigate()
  
  // Create data service instance for budget calculations
  const displayService = useMemo(
    () => new DashboardDataService(expenses, budgets, [], []),
    [expenses, budgets]
  )
  
  const displayBudgetUtilization = useMemo(
    () => displayService.getBudgetUtilization(),
    [displayService]
  )

  if (budgets.length === 0) {
    return (
      <EmptyState
        icon={Wallet}
        title="No Budgets Yet"
        description="Create a budget to control your spending"
        action={
          <Button onClick={() => navigate('/budgets')} variant="primary">
            Create Budget
          </Button>
        }
      />
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="mb-4 flex justify-between items-center">
        <h3 className="text-lg font-bold">Budget Overview</h3>
        <Button onClick={() => navigate('/budgets')} variant="primary" size="sm">
          Manage Budgets
        </Button>
      </div>
      
      <div className="space-y-4">
        {displayBudgetUtilization.map((budget, index) => {
          const isOverBudget = budget.percentage > 100
          const isWarning = budget.percentage >= 90 && budget.percentage < 100

          return (
            <motion.div
              key={budget.id || index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Card className={`${
                isOverBudget 
                  ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20' 
                  : isWarning 
                    ? 'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20'
                    : 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20'
              }`}>
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <p className="font-bold text-gray-900 dark:text-gray-100">{budget.name}</p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {formatCurrency(budget.spent)} of {formatCurrency(budget.allocated)}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-500 mt-1">
                      Remaining: {formatCurrency(budget.remaining)}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className={`font-bold text-lg ${
                      isOverBudget 
                        ? 'text-red-600' 
                        : isWarning 
                          ? 'text-yellow-600'
                          : 'text-blue-600'
                    }`}>
                      {budget.percentage.toFixed(1)}%
                    </p>
                    {isOverBudget && (
                      <div className="flex items-center gap-1 mt-1">
                        <AlertCircle size={16} className="text-red-600" />
                        <span className="text-xs text-red-600 font-semibold">Over Budget</span>
                      </div>
                    )}
                    {isWarning && (
                      <div className="flex items-center gap-1 mt-1">
                        <AlertCircle size={16} className="text-yellow-600" />
                        <span className="text-xs text-yellow-600 font-semibold">Warning</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                  <motion.div
                    className={`h-3 rounded-full ${
                      isOverBudget 
                        ? 'bg-red-600' 
                        : isWarning 
                          ? 'bg-yellow-600'
                          : 'bg-blue-600'
                    }`}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min(budget.percentage, 100)}%` }}
                    transition={{ duration: 0.8 }}
                  />
                </div>
              </Card>
            </motion.div>
          )
        })}
      </div>
    </motion.div>
  )
}
