import React, { useState, useMemo } from 'react'
import { Card, Button, Input, Select, Alert } from '../../components/UI'
import { motion } from 'framer-motion'
import { Zap, TrendingDown } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'

/**
 * Prepayment Scenario Analyzer
 * Shows impact of extra payments on loan
 */
export const PrepaymentAnalyzer = ({ loan, currency = 'USD' }) => {
  const [extraAmount, setExtraAmount] = useState(0)
  const [paymentType, setPaymentType] = useState('one_time') // one_time or recurring
  const [showAnalysis, setShowAnalysis] = useState(false)

  // EMI calculation helper
  const calculateEMI = (principal, rate, months) => {
    if (months <= 0 || principal <= 0) return 0
    const monthlyRate = rate / 12 / 100
    if (monthlyRate === 0) return principal / months
    const numerator = monthlyRate * Math.pow(1 + monthlyRate, months)
    const denominator = Math.pow(1 + monthlyRate, months) - 1
    return principal * (numerator / denominator)
  }

  // Prepayment analysis
  const analysis = useMemo(() => {
    const principal = parseFloat(loan.principal_amount || loan.amount || 0)
    const rate = parseFloat(loan.interest_rate || 0)
    const months = parseInt(loan.loan_term_months || loan.term_months || 0)
    const currentEMI = calculateEMI(principal, rate, months)

    // Current scenario
    const currentTotalInterest = currentEMI * months - principal
    const currentTotalAmount = currentEMI * months
    const currentEndDate = new Date(loan.start_date)
    currentEndDate.setMonth(currentEndDate.getMonth() + months)

    // Prepayment scenarios
    const scenarios = []

    if (paymentType === 'one_time' && extraAmount > 0) {
      // One-time prepayment
      const reducedPrincipal = principal - extraAmount
      if (reducedPrincipal > 0) {
        const newEMI = calculateEMI(reducedPrincipal, rate, months)
        const newTotalInterest = newEMI * months - reducedPrincipal
        const newTotalAmount = newEMI * months + extraAmount
        const newEndDate = new Date(currentEndDate)

        scenarios.push({
          name: `One-time payment of ${formatCurrency(extraAmount, currency)}`,
          type: 'one_time',
          amount: extraAmount,
          monthsSaved: 0, // Not applicable for one-time
          newEMI: newEMI,
          newTotalInterest: Math.max(0, newTotalInterest),
          interestSaved: Math.max(0, currentTotalInterest - newTotalInterest),
          totalAmountSaved: currentTotalAmount - newTotalAmount,
          newEndDate: newEndDate,
        })
      }
    } else if (paymentType === 'recurring' && extraAmount > 0) {
      // Recurring extra payment
      const recurringEMI = currentEMI + extraAmount
      let balance = principal
      let monthCount = 0
      let totalInterestPaid = 0

      while (balance > 0 && monthCount < months * 2) {
        const interestThisMonth = balance * (rate / 12 / 100)
        const principalThisMonth = Math.min(recurringEMI - interestThisMonth, balance)
        
        if (principalThisMonth <= 0) break

        balance -= principalThisMonth
        totalInterestPaid += interestThisMonth
        monthCount++
      }

      const monthsSavedCount = months - monthCount
      const newTotalInterest = totalInterestPaid
      const newTotalAmount = recurringEMI * monthCount
      const interestSavedAmount = currentTotalInterest - newTotalInterest
      const newEndDate = new Date(loan.start_date)
      newEndDate.setMonth(newEndDate.getMonth() + monthCount)

      scenarios.push({
        name: `Extra payment of ${formatCurrency(extraAmount, currency)}/month`,
        type: 'recurring',
        amount: extraAmount,
        monthsSaved: monthsSavedCount,
        newEMI: recurringEMI,
        newTotalInterest: Math.max(0, newTotalInterest),
        interestSaved: Math.max(0, interestSavedAmount),
        totalAmountSaved: (currentEMI * months) - newTotalAmount,
        newEndDate: newEndDate,
        newMonths: monthCount,
      })
    }

    return {
      current: {
        emi: currentEMI,
        totalInterest: Math.max(0, currentTotalInterest),
        totalAmount: currentTotalAmount,
        months: months,
        endDate: currentEndDate,
      },
      scenarios,
    }
  }, [loan, extraAmount, paymentType, currency])

  const scenario = analysis.scenarios[0]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <Card className="p-6 bg-gradient-to-br from-purple-50 to-pink-50 dark:from-purple-900/30 dark:to-pink-900/30 border border-purple-200 dark:border-purple-800">
        <div className="space-y-4">
          {/* Header */}
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-100 dark:bg-purple-800/50 rounded-lg">
              <Zap className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Prepayment Impact Analyzer</h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">See how extra payments reduce your loan tenure</p>
            </div>
          </div>

          {/* Input Section */}
          <div className="pt-2 space-y-4 border-t border-purple-200 dark:border-purple-700">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Extra Payment Amount
              </label>
              <Input
                type="number"
                placeholder="5000"
                value={extraAmount}
                onChange={(e) => setExtraAmount(parseFloat(e.target.value) || 0)}
                step="1000"
                min="0"
                className="w-full"
              />
              <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
                Current EMI: <strong>{formatCurrency(parseFloat(loan.emi_amount || 0), currency)}</strong>
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Payment Type
              </label>
              <Select
                value={paymentType}
                onChange={(e) => setPaymentType(e.target.value)}
                options={[
                  { value: 'one_time', label: 'One-Time Payment' },
                  { value: 'recurring', label: 'Recurring Monthly' },
                ]}
              />
            </div>

            <Button
              onClick={() => setShowAnalysis(true)}
              variant="primary"
              className="w-full"
            >
              Calculate Impact
            </Button>
          </div>
        </div>
      </Card>

      {/* Analysis Results */}
      {showAnalysis && scenario && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Alert */}
          <Alert
            type="success"
            message={`Your ${paymentType === 'one_time' ? 'one-time' : 'extra monthly'} payment will save you ${formatCurrency(scenario.interestSaved, currency)} in interest!`}
          />

          {/* Comparison */}
          <div className="grid grid-cols-2 gap-4">
            {/* Current */}
            <Card className="p-4 bg-white dark:bg-gray-800 border-2 border-gray-200 dark:border-gray-700">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">Current Loan</h4>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Monthly Payment</p>
                  <p className="text-lg font-bold text-blue-600 dark:text-blue-400">{formatCurrency(analysis.current.emi, currency)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Tenure</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{analysis.current.months} months</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Total Interest</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{formatCurrency(analysis.current.totalInterest, currency)}</p>
                </div>
                <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Loan Ends</p>
                  <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">{analysis.current.endDate.toLocaleDateString()}</p>
                </div>
              </div>
            </Card>

            {/* With Prepayment */}
            <Card className="p-4 bg-green-50 dark:bg-green-900/30 border-2 border-green-300 dark:border-green-700">
              <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-4">With {paymentType === 'one_time' ? 'Prepayment' : 'Extra Payment'}</h4>
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Monthly Payment</p>
                  <p className="text-lg font-bold text-green-600 dark:text-green-400">{formatCurrency(scenario.newEMI, currency)}</p>
                </div>
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">New Tenure</p>
                  <p className="text-lg font-bold text-green-600 dark:text-green-400">
                    {paymentType === 'one_time' ? analysis.current.months : scenario.newMonths || analysis.current.months} months
                  </p>
                </div>
                <div>
                  <p className="text-xs text-gray-600 dark:text-gray-400">Total Interest</p>
                  <p className="text-lg font-bold text-green-600 dark:text-green-400">{formatCurrency(scenario.newTotalInterest, currency)}</p>
                </div>
                <div className="pt-2 border-t border-green-300 dark:border-green-700">
                  <p className="text-xs text-gray-600 dark:text-gray-400">Loan Ends</p>
                  <p className="text-sm font-semibold text-green-600 dark:text-green-400">{scenario.newEndDate.toLocaleDateString()}</p>
                </div>
              </div>
            </Card>
          </div>

          {/* Savings Summary */}
          <Card className="p-4 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800">
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4 flex items-center gap-2">
              <TrendingDown className="w-4 h-4 text-green-600 dark:text-green-400" />
              Savings Summary
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Interest Saved</p>
                <p className="text-lg font-bold text-green-600 dark:text-green-400">{formatCurrency(scenario.interestSaved, currency)}</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Time Saved</p>
                <p className="text-lg font-bold text-green-600 dark:text-green-400">
                  {paymentType === 'one_time' ? '-' : `${scenario.monthsSaved} months`}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-600 dark:text-gray-400 mb-1">Total Amount Saved</p>
                <p className="text-lg font-bold text-green-600 dark:text-green-400">{formatCurrency(scenario.totalAmountSaved, currency)}</p>
              </div>
            </div>
          </Card>

          {/* Quick Scenarios */}
          {paymentType === 'recurring' && (
            <Card className="p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800">
              <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-3">💡 Quick Prepayment Options</h4>
              <div className="space-y-2 text-sm">
                {[
                  { pct: 10, label: '10% more (faster payoff)' },
                  { pct: 25, label: '25% more (significant savings)' },
                  { pct: 50, label: '50% more (aggressive prepayment)' },
                ].map((option) => (
                  <button
                    key={option.pct}
                    onClick={() => setExtraAmount(Math.round((parseFloat(loan.emi_amount || 0) * option.pct) / 100))}
                    className="w-full text-left p-2 rounded hover:bg-blue-100 dark:hover:bg-blue-800/50 transition-colors text-gray-900 dark:text-gray-100"
                  >
                    <strong>{option.label}</strong>
                    <br />
                    <span className="text-xs text-gray-600 dark:text-gray-400">
                      Extra: {formatCurrency(Math.round((parseFloat(loan.emi_amount || 0) * option.pct) / 100), currency)}/month
                    </span>
                  </button>
                ))}
              </div>
            </Card>
          )}

          <Button
            onClick={() => setShowAnalysis(false)}
            variant="secondary"
            className="w-full"
          >
            Close Analysis
          </Button>
        </motion.div>
      )}
    </motion.div>
  )
}
