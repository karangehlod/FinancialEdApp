import React from 'react'
import { Card, EmptyState, Button } from '../UI'
import { motion } from 'framer-motion'
import { Zap } from 'lucide-react'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { useNavigate } from 'react-router-dom'

export const LoansTab = ({ loans = [] }) => {
  const navigate = useNavigate()

  if (loans.length === 0) {
    return (
      <EmptyState
        icon={Zap}
        title="No Loans Yet"
        description="Track your loans to manage debt effectively"
        action={
          <Button onClick={() => navigate('/loans')} variant="primary">
            Add Loan
          </Button>
        }
      />
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="mb-4 flex justify-between items-center">
        <h3 className="text-lg font-bold">Active Loans</h3>
        <Button onClick={() => navigate('/loans')} variant="primary" size="sm">
          Manage Loans
        </Button>
      </div>
      
      <div className="space-y-4">
        {loans.map((loan, index) => (
          <motion.div
            key={loan.id}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
          >
            <Card className="border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-gray-900 dark:text-gray-100">{loan.name}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Amount: {formatCurrency(loan.amount)}</p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">Interest: {loan.interest_rate}%</p>
                  {loan.monthly_payment && (
                    <p className="text-sm text-gray-600 dark:text-gray-400">Monthly Payment: {formatCurrency(loan.monthly_payment)}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-lg font-bold text-yellow-600">{formatCurrency(loan.amount)}</p>
                  {loan.due_date && (
                    <p className="text-xs text-gray-500">Due: {formatDate(loan.due_date)}</p>
                  )}
                  {loan.remaining_amount && (
                    <p className="text-sm text-red-600 mt-1">
                      Remaining: {formatCurrency(loan.remaining_amount)}
                    </p>
                  )}
                </div>
              </div>
              
              {/* Progress bar for loan repayment if we have remaining amount */}
              {loan.remaining_amount && (
                <div className="mt-3">
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <motion.div
                      className="bg-yellow-600 h-2 rounded-full"
                      initial={{ width: 0 }}
                      animate={{ 
                        width: `${((parseFloat(loan.amount) - parseFloat(loan.remaining_amount)) / parseFloat(loan.amount)) * 100}%` 
                      }}
                      transition={{ duration: 0.8 }}
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {(((parseFloat(loan.amount) - parseFloat(loan.remaining_amount)) / parseFloat(loan.amount)) * 100).toFixed(1)}% paid off
                  </p>
                </div>
              )}
            </Card>
          </motion.div>
        ))}
      </div>
    </motion.div>
  )
}
