import React from 'react'
import { Card } from '../UI'
import { TrendingUp, Zap } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'
import { motion } from 'framer-motion'

/**
 * EMI Summary Card
 * Displays total monthly EMI commitment across all loans
 */
export const EMISummaryCard = ({ loans = [], currency = 'USD' }) => {
  // Calculate EMI metrics
  const calculateMetrics = () => {
    if (!loans || loans.length === 0) {
      return {
        totalEMI: 0,
        averageEMI: 0,
        minEMI: 0,
        maxEMI: 0,
        loanCount: 0,
      }
    }

    const validLoans = loans.filter(
      (loan) => loan && loan.emi_amount && loan.status === 'active'
    )

    if (validLoans.length === 0) {
      return {
        totalEMI: 0,
        averageEMI: 0,
        minEMI: 0,
        maxEMI: 0,
        loanCount: 0,
      }
    }

    const totalEMI = validLoans.reduce(
      (sum, loan) => sum + parseFloat(loan.emi_amount || 0),
      0
    )
    const averageEMI = totalEMI / validLoans.length
    const emis = validLoans.map((loan) => parseFloat(loan.emi_amount || 0))
    const minEMI = Math.min(...emis)
    const maxEMI = Math.max(...emis)

    return {
      totalEMI,
      averageEMI,
      minEMI,
      maxEMI,
      loanCount: validLoans.length,
    }
  }

  const metrics = calculateMetrics()

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
    >
      <Card className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/30 dark:to-indigo-900/30 border border-blue-200 dark:border-blue-800">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-100 dark:bg-blue-800/50 rounded-lg">
                <Zap className="w-6 h-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400">Monthly EMI Commitment</h3>
                <p className="text-xs text-gray-500 dark:text-gray-500 mt-0.5">
                  Total from {metrics.loanCount} active loan{metrics.loanCount !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
            <TrendingUp style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)', color: 'var(--primary-600, #2563eb)' }} />
          </div>

          {/* Main Amount */}
          <div className="pt-2">
            <p className="font-bold text-blue-900 dark:text-blue-300" style={{ fontSize: 'var(--font-xxl)' }}>
              {formatCurrency(metrics.totalEMI, currency)}
            </p>
            <p className="text-sm text-blue-600 dark:text-blue-400 mt-2">
              {metrics.loanCount > 0
                ? `Paid monthly towards ${metrics.loanCount} loan${metrics.loanCount !== 1 ? 's' : ''}`
                : 'No active loans'}
            </p>
          </div>

          {/* Stats Grid */}
          {metrics.loanCount > 0 && (
            <div className="pt-4 grid grid-cols-3 gap-3 border-t border-blue-200 dark:border-blue-700">
              <div className="text-center">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Average EMI</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100">
                  {formatCurrency(metrics.averageEMI, currency)}
                </p>
              </div>
              <div className="text-center border-l border-r border-blue-200 dark:border-blue-700">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Min - Max</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100 text-sm">
                  {formatCurrency(metrics.minEMI, currency)} - {formatCurrency(metrics.maxEMI, currency)}
                </p>
              </div>
              <div className="text-center">
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Active Loans</p>
                <p className="font-semibold text-gray-900 dark:text-gray-100">{metrics.loanCount}</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {metrics.loanCount === 0 && (
            <div className="pt-4 text-center">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                No active loans. Add a loan to see EMI commitment.
              </p>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  )
}
