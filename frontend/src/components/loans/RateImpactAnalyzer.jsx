import React, { useState, useMemo } from 'react'
import { Card, Button, Input, Alert } from '../../components/UI'
import { motion } from 'framer-motion'
import { TrendingDown, AlertCircle } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'

/**
 * Interest Rate Impact Analyzer
 * Shows what happens if you change the interest rate on a loan
 */
export const RateImpactAnalyzer = ({ loan, currency = 'USD' }) => {
  const [newRate, setNewRate] = useState(loan.interest_rate || 5)
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

  // Calculate metrics
  const analysis = useMemo(() => {
    const principal = parseFloat(loan.principal_amount || loan.amount || 0)
    const currentRate = parseFloat(loan.interest_rate || 0)
    const months = parseInt(loan.loan_term_months || loan.term_months || 0)

    const currentEMI = calculateEMI(principal, currentRate, months)
    const newEMI = calculateEMI(principal, newRate, months)

    const currentTotalInterest = currentEMI * months - principal
    const newTotalInterest = newEMI * months - principal

    const emiSavings = currentEMI - newEMI
    const totalInterestSavings = currentTotalInterest - newTotalInterest
    const totalAmountCurrent = currentEMI * months
    const totalAmountNew = newEMI * months

    return {
      current: {
        emi: currentEMI,
        totalInterest: Math.max(0, currentTotalInterest),
        totalAmount: totalAmountCurrent,
        rate: currentRate,
      },
      new: {
        emi: newEMI,
        totalInterest: Math.max(0, newTotalInterest),
        totalAmount: totalAmountNew,
        rate: newRate,
      },
      savings: {
        monthlyEMI: emiSavings,
        totalInterest: totalInterestSavings,
        totalAmount: totalAmountCurrent - totalAmountNew,
        rateChange: newRate - currentRate,
      },
    }
  }, [loan, newRate, currency])

  const isBeneficial = analysis.savings.totalInterest > 0
  const rateIsLower = analysis.savings.rateChange < 0

  // Render a semantic signed currency value. If `decreased` is true we show a unicode minus (−)
  // to indicate a reduction (savings), otherwise show a plus (+). Use a non-breaking space after sign
  // to avoid the sign being rendered alone due to wrapping or truncation.
  const renderSignedCurrency = (value, decreased) => {
    if (!value) return formatCurrency(0, currency)
    const sign = decreased ? '\u2212' : '+' // unicode minus for clarity
    return `${sign}\u00A0${formatCurrency(Math.abs(value), currency)}`
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <Card className="p-6 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200">
        <div className="space-y-4">
          {/* Input Section */}
          <div className="pt-2 space-y-4 border-t border-blue-200">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                New Interest Rate (%)
              </label>
              <div className="flex gap-2">
                <Input
                  type="number"
                  placeholder="5.5"
                  value={newRate}
                  onChange={(e) => setNewRate(parseFloat(e.target.value) || 0)}
                  step="0.1"
                  min="0"
                  max="50"
                  className="flex-1"
                />
                <span className="flex items-center px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 font-medium">
                  % p.a.
                </span>
              </div>
              <p className="text-xs-fluid text-gray-600 mt-1">
                Current rate: <strong>{analysis.current.rate.toFixed(2)}%</strong>
              </p>
            </div>

            <Button
              onClick={() => setShowAnalysis(true)}
              variant="primary"
              className="w-full"
            >
              Analyze Impact
            </Button>
          </div>
        </div>
      </Card>

      {/* Analysis Results */}
      {showAnalysis && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="space-y-4"
        >
          {/* Alert */}
          {rateIsLower ? (
            <Alert
              type="success"
              message={`Reducing the rate to ${newRate.toFixed(2)}% will save you ${formatCurrency(analysis.savings.totalInterest, currency)} in total interest!`}
            />
          ) : (
            <Alert
              type="warning"
              message={`Increasing the rate to ${newRate.toFixed(2)}% will cost you ${formatCurrency(Math.abs(analysis.savings.totalInterest), currency)} more in interest.`}
            />
          )}

          {/* Comparison Cards */}
          <div className="grid grid-cols-2 gap-4">
            {/* Current Scenario */}
            <Card className="p-4 bg-white border-2 border-gray-200">
              <h4 className="text-sm font-semibold text-gray-700 mb-4">Current Scenario</h4>
              <div className="space-y-3">
                <div>
                  <p className="text-xs-fluid text-gray-600">Interest Rate</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{analysis.current.rate.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-xs-fluid text-gray-600">Monthly EMI</p>
                  <p className="text-lg font-bold text-blue-600">{formatCurrency(analysis.current.emi, currency)}</p>
                </div>
                <div>
                  <p className="text-xs-fluid text-gray-600">Total Interest</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{formatCurrency(analysis.current.totalInterest, currency)}</p>
                </div>
                <div className="pt-2 border-t border-gray-200">
                  <p className="text-xs text-gray-600">Total Amount to Pay</p>
                  <p className="text-lg font-bold text-gray-900">{formatCurrency(analysis.current.totalAmount, currency)}</p>
                </div>
              </div>
            </Card>

            {/* New Scenario */}
            <Card className={`p-4 border-2 ${isBeneficial ? 'bg-green-50 border-green-300' : 'bg-red-50 border-red-300'}`}>
              <h4 className="text-sm font-semibold text-gray-700 mb-4">New Scenario @ {newRate.toFixed(2)}%</h4>
              <div className="space-y-3">
                <div>
                  <p className="text-xs-fluid text-gray-600">Interest Rate</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{newRate.toFixed(2)}%</p>
                </div>
                <div>
                  <p className="text-xs-fluid text-gray-600">Monthly EMI</p>
                  <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(analysis.new.emi, currency)}
                  </p>
                </div>
                <div>
                  <p className="text-xs-fluid text-gray-600">Total Interest</p>
                  <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(analysis.new.totalInterest, currency)}
                  </p>
                </div>
                <div className="pt-2 border-t border-gray-200">
                  <p className="text-xs text-gray-600">Total Amount to Pay</p>
                  <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                    {formatCurrency(analysis.new.totalAmount, currency)}
                  </p>
                </div>
              </div>
            </Card>
          </div>

          {/* Savings Breakdown */}
          <Card className={`p-4 ${isBeneficial ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <h4 className="text-sm font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <TrendingDown className={`icon-sm ${isBeneficial ? 'text-green-600' : 'text-red-600'}`} />
              Impact Summary
            </h4>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-xs text-gray-600 mb-1">Monthly EMI Change</p>
                <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                  {renderSignedCurrency(analysis.savings.monthlyEMI, isBeneficial)}
                </p>
                <p className="text-xs text-gray-600 mt-1">{isBeneficial ? 'Save' : 'Pay'} per month</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Total Interest Savings</p>
                <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                  {renderSignedCurrency(analysis.savings.totalInterest, isBeneficial)}
                </p>
                <p className="text-xs text-gray-600 mt-1">Over loan period</p>
              </div>
              <div>
                <p className="text-xs text-gray-600 mb-1">Total Amount Saved</p>
                <p className={`text-lg font-bold ${isBeneficial ? 'text-green-600' : 'text-red-600'}`}>
                  {renderSignedCurrency(analysis.savings.totalAmount, isBeneficial)}
                </p>
                <p className="text-xs text-gray-600 mt-1">Overall</p>
              </div>
            </div>
          </Card>

          {/* Recommendation */}
          <Card className="p-4 bg-blue-50 border border-blue-200">
            <div className="flex gap-3">
              <AlertCircle style={{ width: 'var(--icon-sm)', height: 'var(--icon-sm)' }} className="text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-blue-900">
                {isBeneficial ? (
                  <>
                    <p className="font-semibold mb-1">✓ Worth Refinancing</p>
                    <p>
                      You would save <strong>{formatCurrency(analysis.savings.totalInterest, currency)}</strong> in interest
                      by refinancing to {newRate.toFixed(2)}%. This reduces your monthly payment
                      by <strong>{formatCurrency(analysis.savings.monthlyEMI, currency)}</strong>.
                    </p>
                  </>
                ) : (
                  <>
                    <p className="font-semibold mb-1">✗ Not Recommended</p>
                    <p>
                      Refinancing to {newRate.toFixed(2)}% would cost you an additional{' '}
                      <strong>{formatCurrency(Math.abs(analysis.savings.totalInterest), currency)}</strong> in interest.
                      Keep your current rate of {analysis.current.rate.toFixed(2)}%.
                    </p>
                  </>
                )}
              </div>
            </div>
          </Card>

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
