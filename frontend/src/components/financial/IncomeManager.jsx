import React, { useState, useEffect } from 'react'
import { Card, Button, Input, Alert } from '../../components/UI'
import { motion } from 'framer-motion'
import { DollarSign, TrendingUp } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'

/**
 * Income Manager Component
 * Allows users to set and manage their monthly income
 */
export const IncomeManager = ({
  initialIncome = 0,
  currency = 'USD',
  onSave = null,
  isLoading = false,
}) => {
  const [income, setIncome] = useState(initialIncome || 0)
  const [annualMode, setAnnualMode] = useState(false)
  const [isSaving, setIsSaving] = useState(false)

  // Sync with initialIncome when it loads from the server
  useEffect(() => {
    if (initialIncome && initialIncome !== income) {
      setIncome(initialIncome)
    }
  }, [initialIncome])

  // Convert between annual and monthly
  const getDisplayIncome = () => {
    return annualMode ? (income * 12) : income
  }

  const getActualMonthlyIncome = () => {
    return annualMode ? (income / 12) : income
  }

  const handleIncomeChange = (e) => {
    const value = parseFloat(e.target.value) || 0
    setIncome(value)
  }

  const handleToggleMode = () => {
    // When toggling, convert the current value
    if (annualMode) {
      // Converting from annual to monthly display
      setIncome(getActualMonthlyIncome())
    } else {
      // Converting from monthly to annual display
      setIncome(income * 12)
    }
    setAnnualMode(!annualMode)
  }

  const handleSave = async () => {
    if (onSave) {
      setIsSaving(true)
      try {
        await onSave({
          monthly_salary: getActualMonthlyIncome(),
        })
      } catch (error) {
        console.error('Failed to save income:', error)
      } finally {
        setIsSaving(false)
      }
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-4"
    >
      <Card className="p-6 bg-gradient-to-br from-green-50 to-emerald-50 dark:from-green-900/30 dark:to-emerald-900/30 border border-green-200 dark:border-green-800">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <div className="p-3 bg-green-100 dark:bg-green-800/50 rounded-lg">
            <DollarSign className="w-6 h-6 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Monthly Income</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400">Manage your primary income source</p>
          </div>
        </div>

        {/* Income Display */}
        <div className="mb-6 p-4 bg-white dark:bg-gray-800 rounded-lg border border-green-200 dark:border-green-700">
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
            {annualMode ? 'Annual Income' : 'Monthly Income'}
          </p>
          <p className="font-bold text-green-600 dark:text-green-400" style={{ fontSize: 'var(--font-xxl)' }}>
            {formatCurrency(getDisplayIncome(), currency)}
          </p>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-2">
            {annualMode
              ? `Monthly: ${formatCurrency(getActualMonthlyIncome(), currency)}`
              : `Annual: ${formatCurrency(income * 12, currency)}`}
          </p>
        </div>

        {/* Input Section */}
        <div className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              {annualMode ? 'Annual Income' : 'Monthly Income'}
            </label>
            <div className="flex gap-2">
              <Input
                type="number"
                placeholder={annualMode ? '600000' : '50000'}
                value={income}
                onChange={handleIncomeChange}
                step="1000"
                min="0"
                className="flex-1"
              />
              <Button
                variant="secondary"
                onClick={handleToggleMode}
                className="px-4"
              >
                {annualMode ? 'Annual' : 'Monthly'}
              </Button>
            </div>
          </div>

          {/* Info Alert */}
          <Alert
            type="info"
            message={`Income will be used to calculate your available savings each month. All calculations use the monthly amount internally.`}
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Button
            onClick={handleSave}
            isLoading={isSaving || isLoading}
            disabled={income === initialIncome}
            className="flex-1"
          >
            <TrendingUp className="w-4 h-4 mr-2" />
            Save Income
          </Button>
        </div>
      </Card>

      {/* Usage Info */}
      <Card className="p-4 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800">
        <h4 className="text-sm font-semibold text-blue-900 dark:text-blue-300 mb-2">How this is used:</h4>
        <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
          <li>✓ Calculates available savings: Income - EMI - Expenses</li>
          <li>✓ Shows spending percentage relative to income</li>
          <li>✓ Helps with goal allocation and budgeting</li>
          <li>✓ Provides savings rate metrics and trends</li>
        </ul>
      </Card>
    </motion.div>
  )
}
