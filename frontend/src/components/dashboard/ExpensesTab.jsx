import React from 'react'
import { Card, EmptyState, Button } from '../UI'
import { motion } from 'framer-motion'
import { TrendingDown } from 'lucide-react'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { useNavigate } from 'react-router-dom'

export const ExpensesTab = ({ expenses = [] }) => {
  const navigate = useNavigate()

  if (expenses.length === 0) {
    return (
      <EmptyState
        icon={TrendingDown}
        title="No Expenses Yet"
        description="Start tracking your spending by adding your first expense"
        action={
          <Button onClick={() => navigate('/expenses')} variant="primary">
            Add Expense
          </Button>
        }
      />
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="mb-4 flex justify-between items-center">
        <h3 className="text-lg font-bold">Recent Expenses</h3>
        <Button onClick={() => navigate('/expenses')} variant="primary" size="sm">
          View All Expenses
        </Button>
      </div>
      
      <Card>
        <div className="space-y-3">
          {expenses.slice(0, 10).map((expense, index) => (
            <motion.div
              key={expense.id}
              className="flex items-center justify-between p-4 bg-gradient-to-r from-red-50 to-pink-50 dark:from-red-900/20 dark:to-pink-900/20 rounded-lg border border-red-100 dark:border-red-800 hover:shadow-md transition-shadow"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <div className="flex-1">
                <p className="font-bold text-gray-900 dark:text-gray-100">{expense.category}</p>
                <p className="text-sm text-gray-600 dark:text-gray-400">{expense.description}</p>
                <p className="text-xs text-gray-400 mt-1">{formatDate(expense.date)}</p>
              </div>
              <p className="font-bold text-lg text-red-600 dark:text-red-400">{formatCurrency(expense.amount)}</p>
            </motion.div>
          ))}
        </div>
        
        {expenses.length > 10 && (
          <div className="mt-4 text-center">
            <Button onClick={() => navigate('/expenses')} variant="secondary">
              View All {expenses.length} Expenses
            </Button>
          </div>
        )}
      </Card>
    </motion.div>
  )
}
