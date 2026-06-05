import React, { useEffect, useState } from 'react'
import { Card, LoadingSpinner } from '../UI'
import { motion } from 'framer-motion'
import { TrendingUp, PieChart } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'

type Metrics = {
  availableToSave: number
  savingsRate: number
  budgetPercentage: number
  emiPercentage: number
  incomePercentage: number
}

interface MonthlySavingsTrackerProps {
  monthlyIncome?: number
  totalEMI?: number
  totalBudget?: number
  currency?: string
  isLoading?: boolean
}

export const MonthlySavingsTracker: React.FC<MonthlySavingsTrackerProps> = ({
  monthlyIncome = 0,
  totalEMI = 0,
  totalBudget = 0,
  currency = 'USD',
  isLoading = false,
}) => {
  const [metrics, setMetrics] = useState<Metrics>({
    availableToSave: 0,
    savingsRate: 0,
    budgetPercentage: 0,
    emiPercentage: 0,
    incomePercentage: 100,
  })

  useEffect(() => {
    if (monthlyIncome > 0) {
      const availableToSave = monthlyIncome - totalBudget - totalEMI
      const savingsRate = availableToSave > 0 ? (availableToSave / monthlyIncome) * 100 : 0
      const budgetPercentage = (totalBudget / monthlyIncome) * 100
      const emiPercentage = (totalEMI / monthlyIncome) * 100

      setMetrics({
        availableToSave: Math.max(0, availableToSave),
        savingsRate: Math.max(0, savingsRate),
        budgetPercentage: Math.min(100, isFinite(budgetPercentage) ? budgetPercentage : 0),
        emiPercentage: Math.min(100, isFinite(emiPercentage) ? emiPercentage : 0),
        incomePercentage: 100,
      })
    }
  }, [monthlyIncome, totalBudget, totalEMI])

  if (isLoading) {
    return (
      <Card className="flex items-center justify-center p-[var(--spacing-md)] min-h-[var(--placeholder-height)]">
        <LoadingSpinner size="lg" />
      </Card>
    )
  }

  const getSavingsStatus = () => {
    if (metrics.savingsRate >= 30)
      return {
        textColor: '#16a34a',
        borderColor: '#16a34a',
        borderLightColor: '#bbf7d0',
        bgClass: 'bg-green-50',
        label: 'Excellent',
      }
    if (metrics.savingsRate >= 20)
      return {
        textColor: '#2563eb',
        borderColor: '#2563eb',
        borderLightColor: '#dbeafe',
        bgClass: 'bg-blue-50',
        label: 'Good',
      }
    if (metrics.savingsRate >= 10)
      return {
        textColor: '#d97706',
        borderColor: '#d97706',
        borderLightColor: '#fff7ed',
        bgClass: 'bg-yellow-50',
        label: 'Fair',
      }
    return {
      textColor: '#dc2626',
      borderColor: '#dc2626',
      borderLightColor: '#fee2e2',
      bgClass: 'bg-red-50',
      label: 'Low',
    }
  }

  const status = getSavingsStatus()

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
      <Card className={`border-l-4 ${status.bgClass}`}>
        <div style={{ padding: 'var(--spacing-md)', borderLeftColor: status.borderColor }} className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-white dark:bg-gray-800 rounded-lg border-2" style={{ padding: 'var(--spacing-sm)', borderColor: status.borderLightColor }}>
                <TrendingUp style={{ width: 'var(--icon-md)', height: 'var(--icon-md)', color: status.textColor }} />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Available to Save</h3>
                <p className="text-sm" style={{ color: status.textColor }}>{status.label} savings rate</p>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg" style={{ padding: 'var(--spacing-md)' }}>
            <div className="flex items-center justify-between gap-4" style={{ flexWrap: 'wrap' }}>
              <div style={{ minWidth: 0 }}>
                <p className="font-bold" style={{ fontSize: 'var(--font-xl)', color: status.textColor, margin: 0, wordBreak: 'break-word' }}>
                  {formatCurrency(metrics.availableToSave, currency)}
                </p>
                <p className="text-gray-600 dark:text-gray-400" style={{ fontSize: 'var(--font-sm)', marginTop: 'var(--spacing-xs)' }}>
                  {metrics.savingsRate.toFixed(1)}% of your income available for goals and savings
                </p>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
                <div style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0.25rem 0.6rem',
                  borderRadius: '9999px',
                  backgroundColor: status.borderLightColor || 'rgba(0,0,0,0.04)'
                }}>
                  <span style={{ fontSize: 'var(--font-sm)', fontWeight: 700, color: status.borderColor }}>{metrics.savingsRate.toFixed(1)}%</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: 'var(--font-sm)', fontWeight: 600, color: status.textColor }}>{status.label}</div>
                  <div style={{ fontSize: '12px', color: 'var(--muted-text, #6b7280)' }}>of income</div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Monthly Breakdown</h4>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Income</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(monthlyIncome, currency)}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full" style={{ height: 'var(--progress-height)' }}>
                <div className="bg-green-500 rounded-full" style={{ width: '100%', height: 'var(--progress-height)' }} />
              </div>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Loan EMI</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(totalEMI, currency)}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full" style={{ height: 'var(--progress-height)' }}>
                <div className="bg-orange-500 rounded-full" style={{ width: `${Math.min(100, metrics.emiPercentage)}%`, height: 'var(--progress-height)' }} />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 text-right">{metrics.emiPercentage.toFixed(1)}% of income</p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600 dark:text-gray-400">Budget Allocated</span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(totalBudget, currency)}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full" style={{ height: 'var(--progress-height)' }}>
                <div className="bg-blue-500 rounded-full" style={{ width: `${Math.min(100, metrics.budgetPercentage)}%`, height: 'var(--progress-height)' }} />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 text-right">{metrics.budgetPercentage.toFixed(1)}% of income</p>
            </div>

            <div className="space-y-1 pt-2 border-t border-gray-300 dark:border-gray-600">
              <div className="flex items-center justify-between">
                <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">Available to Save</span>
                <span className="font-bold text-lg" style={{ color: status.textColor }}>{formatCurrency(metrics.availableToSave, currency)}</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full" style={{ height: 'var(--progress-height)' }}>
                <div className="h-2 rounded-full" style={{ width: `${Math.min(100, metrics.savingsRate)}%`, height: 'var(--progress-height)', backgroundColor: status.textColor }} />
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 text-right">{metrics.savingsRate.toFixed(1)}% of income</p>
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
            <div className="flex gap-2 text-sm">
              <PieChart style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)', color: 'var(--muted-text, #4b5563)' }} />
              <div>
                <p className="font-medium text-gray-700 dark:text-gray-300">💡 Savings Tip</p>
                <p className="text-gray-600 dark:text-gray-400">
                  {metrics.savingsRate >= 20
                    ? `Great job! You're saving ${metrics.savingsRate.toFixed(1)}% of your income. Consider allocating this to your financial goals.`
                    : metrics.savingsRate > 0
                    ? `You're on track. Look for ways to increase savings by reducing expenses or increasing income.`
                    : `Your expenses exceed your income. Consider reducing expenses or increasing your income.`}
                </p>
              </div>
            </div>
          </div>
        </div>
      </Card>

      <Card className="bg-blue-50 dark:bg-blue-900/30 rounded-lg border border-blue-200 dark:border-blue-800 p-[var(--spacing-sm)]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex-shrink-0">
            <div className="w-[var(--icon-md)] h-[var(--icon-md)] rounded-md flex items-center justify-center bg-blue-100 dark:bg-blue-800">
              <svg aria-hidden width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-600 dark:text-blue-300">
                <path d="M13 16h-1v-4h-1" />
                <circle cx="12" cy="8" r="1" />
              </svg>
            </div>
          </div>

          <div className="flex-1">
            <h4 className="text-sm font-semibold text-gray-800 dark:text-gray-100">How Savings are Calculated</h4>
            <p className="text-sm text-gray-600 dark:text-gray-300 mt-1 mb-2">Formula:</p>

            <div className="flex flex-wrap items-center gap-2 mb-3">
              <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-sm font-medium">Income</span>
              <span className="text-sm">−</span>
              <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-sm font-medium">EMI (Loans)</span>
              <span className="text-sm">−</span>
              <span className="px-2 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-sm font-medium">Budgeted Expenses</span>
              <span className="text-sm">=</span>
              <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-800 text-sm font-semibold">Available to Save</span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm text-gray-700 dark:text-gray-200">
              <div className="flex justify-between"><span>Monthly Income</span><strong>{formatCurrency(monthlyIncome, currency)}</strong></div>
              <div className="flex justify-between"><span>Total EMI</span><strong>{formatCurrency(totalEMI, currency)}</strong></div>
              <div className="flex justify-between"><span>Budgeted Expenses</span><strong>{formatCurrency(totalBudget, currency)}</strong></div>
              <div className="flex justify-between"><span>Available to Save</span><strong className="" style={{ color: status.textColor }}>{formatCurrency(metrics.availableToSave, currency)}</strong></div>
            </div>

            <p className="mt-3 text-xs text-gray-600 dark:text-gray-300">If Available to Save is negative, your total expenses (EMI + Budget) exceed your income. Reduce budgeted expenses, refinance loans, or increase income to improve savings.</p>
          </div>
        </div>
      </Card>
    </motion.div>
  )
}
