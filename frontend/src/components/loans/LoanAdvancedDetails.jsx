import React, { useState, useMemo, useEffect } from 'react'
import { Card, Button, Input, Modal, FluidIcon } from '../UI'
import PageHeader from '../layout/PageHeader'
import { RateImpactAnalyzer } from './RateImpactAnalyzer'
import { PrepaymentAnalyzer } from './PrepaymentAnalyzer'
import { motion } from 'framer-motion'
import { TrendingDown, Calendar, DollarSign, Clock } from 'lucide-react'
import { formatCurrency, formatDate } from '../../utils/helpers'
import { loanService } from '../../services/apiService'
import { showErrorToast, showSuccessToast } from '../../utils/toast'

/**
 * Calculate EMI (Equated Monthly Installment)
 * Formula: EMI = P × r × (1+r)^n / ((1+r)^n - 1)
 */
const calculateEMI = (principal, annualRate, months) => {
  if (!isFinite(principal) || !isFinite(annualRate) || !isFinite(months) || months <= 0 || principal <= 0) return 0

  const monthlyRate = annualRate / 12 / 100

  if (monthlyRate === 0) {
    return principal / months
  }

  const numerator = monthlyRate * Math.pow(1 + monthlyRate, months)
  const denominator = Math.pow(1 + monthlyRate, months) - 1
  const emi = principal * (numerator / denominator)

  return Math.round(emi * 100) / 100
}

const calculateTotalInterest = (principal, emi, months) => {
  if (!isFinite(principal) || !isFinite(emi) || !isFinite(months)) return 0
  const totalPaid = emi * months
  return Math.round((totalPaid - principal) * 100) / 100
}

const calculateEndDate = (startDate, months) => {
  try {
    const date = new Date(startDate)
    if (isNaN(date.getTime())) return null
    date.setMonth(date.getMonth() + (Number.isFinite(months) ? months : 0))
    return date
  } catch (e) {
    return null
  }
}

const calculateRemainingMonths = (startDate, totalMonths) => {
  try {
    const start = new Date(startDate)
    if (isNaN(start.getTime()) || !Number.isFinite(totalMonths)) return 0
    const today = new Date()
    const monthsDifference = (today.getFullYear() - start.getFullYear()) * 12 + (today.getMonth() - start.getMonth())
    const remaining = totalMonths - Math.max(0, monthsDifference)
    return Math.max(0, remaining)
  } catch (e) {
    return 0
  }
}

export const LoanAdvancedDetails = ({ loan, onClose }) => {
  // Guard: if no loan provided, render a minimal message to avoid runtime errors
  if (!loan) {
    return (
      <div className="p-6">
        <PageHeader title="Loan Details" subtitle="No loan selected" aria-hidden={false} />
        <Card className="p-4">
          <p className="text-sm-fluid">No loan data available.</p>
          <div className="mt-4">
            <Button onClick={onClose} variant="secondary">Close</Button>
          </div>
        </Card>
      </div>
    )
  }

  const [remoteLoan, setRemoteLoan] = useState(null)
  const [remoteSchedule, setRemoteSchedule] = useState([])
  const [loadingRemote, setLoadingRemote] = useState(false)
  const [editingStartDate, setEditingStartDate] = useState(false)
  const [newStartDate, setNewStartDate] = useState(loan?.start_date || '')
  const [savingStartDate, setSavingStartDate] = useState(false)
  const [showCustomEMI, setShowCustomEMI] = useState(false)
  const [customEMI, setCustomEMI] = useState('')
  const [showRateImpact, setShowRateImpact] = useState(false)
  const [showPrepayment, setShowPrepayment] = useState(false)

  const principal = parseFloat(loan.principal_amount ?? loan.amount ?? 0)
  const annualRate = parseFloat(loan.interest_rate ?? 0)
  const months = parseInt(loan.loan_term_months ?? loan.term_months ?? 0)

  // Fetch authoritative loan info (outstanding balance, payments remaining, schedule)
  useEffect(() => {
    let mounted = true
    const fetchRemote = async () => {
      if (!loan || !loan.id) return
      setLoadingRemote(true)
      try {
        const fresh = await loanService.getOne(loan.id)
        const schedule = await loanService.getSchedule(loan.id)
        if (!mounted) return
        setRemoteLoan(fresh)
        setRemoteSchedule(Array.isArray(schedule) ? schedule : [])
      } catch (err) {
        console.error('Failed to fetch loan summary/schedule', err)
      } finally {
        if (mounted) setLoadingRemote(false)
      }
    }

    fetchRemote()
    return () => { mounted = false }
  }, [loan?.id])

  const emiAmount = loan.emi_amount ? parseFloat(loan.emi_amount) : calculateEMI(principal, annualRate, months)
  const totalInterest = calculateTotalInterest(principal, emiAmount, months)
  const totalAmount = Math.round((principal + totalInterest) * 100) / 100
  const endDate = calculateEndDate(remoteLoan?.start_date ?? loan.start_date, months)

  const remainingMonthsFromBackend = remoteLoan?.payments_remaining ?? remoteLoan?.remaining_months
  const remainingMonthsFromSchedule = remoteSchedule ? remoteSchedule.filter((s) => !s.is_paid).length : null
  const remainingMonths = remainingMonthsFromBackend ?? remainingMonthsFromSchedule ?? calculateRemainingMonths(remoteLoan?.start_date ?? loan.start_date, months)

  const outstandingBalance = (() => {
    const remoteOutstanding = remoteLoan?.remaining_principal ?? remoteLoan?.outstanding_balance
    if (remoteOutstanding !== undefined && remoteOutstanding !== null) return parseFloat(remoteOutstanding)
    if (loan.outstanding_balance !== undefined && loan.outstanding_balance !== null) return parseFloat(loan.outstanding_balance)
    return principal
  })()

  const customEMIValue = customEMI ? parseFloat(customEMI) : null
  const customAnalysis = useMemo(() => {
    if (!customEMIValue || customEMIValue <= 0) return null
    const monthlyRate = annualRate / 12 / 100

    if (monthlyRate === 0) {
      const newMonths = Math.ceil(principal / customEMIValue)
      return {
        newMonths,
        newTotalInterest: 0,
        newTotalAmount: principal,
        saveMonths: months - newMonths,
        saveMoney: totalInterest,
      }
    }

    const monthlyPaymentOnPrincipal = customEMIValue - (principal * monthlyRate)
    if (monthlyPaymentOnPrincipal <= 0) {
      return {
        error: 'EMI must be higher than monthly interest (' + formatCurrency(principal * monthlyRate) + ')',
      }
    }

    const newMonths = Math.ceil(
      Math.log(customEMIValue / (customEMIValue - principal * monthlyRate)) /
      Math.log(1 + monthlyRate)
    )

    const newTotalInterest = (customEMIValue * newMonths) - principal
    return {
      newMonths,
      newTotalInterest: Math.round(newTotalInterest * 100) / 100,
      newTotalAmount: Math.round((principal + newTotalInterest) * 100) / 100,
      saveMonths: Math.max(0, months - newMonths),
      saveMoney: Math.round((totalInterest - newTotalInterest) * 100) / 100,
    }
  }, [customEMI, principal, annualRate, months, totalInterest])

  const monthlyRate = (annualRate / 12).toFixed(2)
  const emiToIncomeRatio = loan.monthly_income ? ((emiAmount / parseFloat(loan.monthly_income)) * 100).toFixed(2) : null
  const startDateDisplay = remoteLoan?.start_date ?? loan?.start_date

  const handleEditStartDate = () => {
    setNewStartDate(startDateDisplay)
    setEditingStartDate(true)
  }

  const handleCancelEdit = () => {
    setEditingStartDate(false)
    setNewStartDate(startDateDisplay)
  }

  const handleSaveStartDate = async () => {
    if (!newStartDate) {
      showErrorToast('Please select a valid start date')
      return
    }

    const selected = new Date(newStartDate)
    const today = new Date()
    const selISO = selected.toISOString().slice(0, 10)
    const todayISO = today.toISOString().slice(0, 10)
    if (selISO > todayISO) {
      showErrorToast('Start date cannot be in the future')
      return
    }

    const normalized = selISO
    setSavingStartDate(true)
    try {
      const updated = await loanService.update(loan.id, { start_date: normalized })
      const fresh = await loanService.getOne(loan.id)
      const schedule = await loanService.getSchedule(loan.id)
      setRemoteLoan(fresh)
      setRemoteSchedule(Array.isArray(schedule) ? schedule : [])
      setEditingStartDate(false)
      showSuccessToast('Loan start date updated')
    } catch (err) {
      console.error('Failed to update start date', err)
      showErrorToast(err?.response?.data?.detail || 'Failed to update start date')
    } finally {
      setSavingStartDate(false)
    }
  }

  return (
    <div>
      <PageHeader
        title={`Loan Details`}
        subtitle={`Loan ending in ${loan.account_number ? loan.account_number.slice(-4) : ''}`}
        icon={<FluidIcon icon={TrendingDown} className="icon-lg text-blue-600" aria-hidden={true} />}
        actions={(
          <div className="flex items-center gap-2">
            <Button onClick={onClose} variant="ghost" size="sm">Close</Button>
          </div>
        )}
      />

      <motion.div
        className="space-y-6 text-gray-900 dark:text-gray-100 fluid-container"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
      >
        {/* Key Metrics Grid (responsive) */}
        <div className="fluid-grid">
          {/* EMI */}
          <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20 h-full flex flex-col justify-between overflow-hidden">
            <div className="flex items-start justify-between min-w-0 gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="text-xs-fluid text-gray-600 mb-1 truncate">Monthly EMI</p>
                <p className="text-lg-fluid font-bold text-blue-600 dark:text-blue-400 truncate" aria-live="polite">{formatCurrency(emiAmount)}</p>
              </div>
              <FluidIcon icon={DollarSign} className="icon-md text-blue-600 opacity-60" aria-hidden={true} />
            </div>
          </Card>

          {/* Outstanding Principal (backend when available) */}
          <Card className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20 h-full flex flex-col justify-between overflow-hidden">
            <div className="flex items-start justify-between min-w-0 gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="text-xs-fluid text-gray-600 mb-1 truncate">Outstanding Principal</p>
                <p className="text-lg-fluid font-bold text-orange-600 dark:text-orange-400 truncate" aria-live="polite">{formatCurrency(outstandingBalance)}</p>
                {remoteLoan && (
                  <p className="text-xs-fluid text-gray-500 mt-1 truncate">(Updated from server)</p>
                )}
              </div>
              <FluidIcon icon={TrendingDown} className="icon-md text-orange-600 opacity-60" aria-hidden={true} />
            </div>
          </Card>

          {/* End Date */}
          <Card className="p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20 h-full flex flex-col justify-between overflow-hidden">
            <div className="flex items-center justify-between min-w-0 gap-3 flex-wrap">
              <div className="min-w-0 flex-1" role="region" aria-labelledby="loan-enddate">
                <p id="loan-enddate" className="text-xs-fluid text-gray-600 mb-1 truncate">End Date</p>
                <div className="flex items-center gap-3 min-w-0 flex-wrap">
                  <p className="text-sm-fluid font-bold text-green-600 dark:text-green-400 truncate">{endDate ? formatDate(endDate) : '—'}</p>

                  {/* Edit start date control */}
                  {!editingStartDate ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleEditStartDate}
                      className="!px-2 !py-1"
                      title="Edit loan start date"
                      aria-expanded={editingStartDate}
                    >
                      Edit start date
                    </Button>
                  ) : (
                    <div className="flex items-center gap-2 min-w-0">
                      <Input
                        type="date"
                        value={newStartDate ? newStartDate.slice(0,10) : ''}
                        onChange={(e) => setNewStartDate(e.target.value)}
                        max={new Date().toISOString().slice(0,10)}
                        className="w-auto input-fluid"
                        aria-label="Edit loan start date"
                      />
                      <Button onClick={handleSaveStartDate} disabled={savingStartDate} size="sm" variant="secondary">
                        {savingStartDate ? 'Saving...' : 'Save'}
                      </Button>
                      <Button onClick={handleCancelEdit} size="sm" variant="outline">
                        Cancel
                      </Button>
                    </div>
                  )}
                </div>
              </div>

              <FluidIcon icon={Calendar} className="icon-md text-green-600 opacity-60" aria-hidden={true} />
            </div>
          </Card>

          {/* Remaining Months */}
          <Card className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20 h-full flex flex-col justify-between overflow-hidden">
            <div className="flex items-start justify-between min-w-0 gap-3 flex-wrap">
              <div className="min-w-0">
                <p className="text-xs-fluid text-gray-600 mb-1 truncate">Remaining</p>
                <p className="text-lg-fluid font-bold text-purple-600 dark:text-purple-400 truncate">{remainingMonths}</p>
                <p className="text-xs-fluid text-gray-500 truncate">months</p>
              </div>
              <FluidIcon icon={Clock} className="icon-md text-purple-600 opacity-60" aria-hidden={true} />
            </div>
          </Card>
        </div>

        {/* Summary Section (responsive) */}
        <Card className="p-6 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 border-l-4 border-slate-400 dark:border-slate-700 overflow-hidden">
          <h3 className="text-lg-fluid font-semibold text-gray-900 dark:text-gray-100 mb-4">Loan Summary</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 text-sm-fluid">
            <div className="min-w-0 break-words w-full">
              <p className="text-gray-600 dark:text-gray-400">Principal Amount</p>
              <p className="font-bold text-gray-900 dark:text-gray-100 truncate">{formatCurrency(principal)}</p>
            </div>
            <div className="min-w-0 break-words w-full">
              <p className="text-gray-600 dark:text-gray-400">Total Amount (P + I)</p>
              <p className="font-bold text-gray-900 dark:text-gray-100 truncate">{formatCurrency(totalAmount)}</p>
            </div>
            <div className="min-w-0 break-words w-full">
              <p className="text-gray-600 dark:text-gray-400">Total Loan Tenure</p>
              <p className="font-bold text-gray-900 dark:text-gray-100">{months} months</p>
            </div>
            <div className="min-w-0 break-words w-full">
              <p className="text-gray-600 dark:text-gray-400">Annual Interest Rate</p>
              <p className="font-bold text-gray-900 dark:text-gray-100">{annualRate}%</p>
            </div>
            <div className="min-w-0 break-words w-full">
              <p className="text-gray-600 dark:text-gray-400">Monthly Interest Rate</p>
              <p className="font-bold text-gray-900 dark:text-gray-100">{monthlyRate}%</p>
            </div>
            {emiToIncomeRatio && (
              <div className="min-w-0 break-words w-full">
                <p className="text-gray-600 dark:text-gray-400">EMI to Income Ratio</p>
                <p className="font-bold text-gray-900 dark:text-gray-100">{emiToIncomeRatio}%</p>
              </div>
            )}
          </div>
        </Card>

        {/* Breakdown Section (responsive tiles) */}
        <Card className="p-6 overflow-hidden">
          <h3 className="text-lg-fluid font-semibold text-gray-900 dark:text-gray-100 mb-4">Payment Breakdown</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg min-w-0 flex items-center justify-between">
              <span className="text-gray-700 dark:text-gray-200 text-sm-fluid break-words">Monthly Payment (EMI)</span>
              <span className="font-bold text-blue-600 dark:text-blue-400 text-lg-fluid truncate" aria-live="polite">{formatCurrency(emiAmount)}</span>
            </div>
            <div className="p-3 bg-orange-50 dark:bg-orange-900/10 rounded-lg min-w-0 flex items-center justify-between">
              <span className="text-gray-700 dark:text-gray-200 text-sm-fluid break-words">Total Interest Over {months} months</span>
              <span className="font-bold text-orange-600 dark:text-orange-400 text-lg-fluid truncate">{formatCurrency(totalInterest)}</span>
            </div>
            <div className="p-3 bg-green-50 dark:bg-green-900/10 rounded-lg min-w-0 flex items-center justify-between">
              <span className="text-gray-700 dark:text-gray-200 text-sm-fluid break-words">Total Amount to Pay</span>
              <span className="font-bold text-green-600 dark:text-green-400 text-lg-fluid truncate">{formatCurrency(totalAmount)}</span>
            </div>
          </div>
        </Card>

        {/* Custom EMI Analysis */}
        <motion.div
          layout
          className="space-y-4"
        >
          <Button
            onClick={() => setShowCustomEMI(!showCustomEMI)}
            variant="secondary"
            className="w-full"
            aria-expanded={showCustomEMI}
          >
            {showCustomEMI ? '✕ Close Custom EMI Calculator' : '+ Try Custom EMI'}
          </Button>

          {showCustomEMI && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              <Card className="p-6 bg-gradient-to-br from-indigo-50 to-indigo-100">
                <h3 className="text-lg-fluid font-semibold text-gray-900 dark:text-gray-100 mb-4">Custom EMI Scenario</h3>
                <p className="text-sm-fluid text-gray-600 mb-4">
                  See how a different monthly payment affects your loan timeline and total interest.
                </p>
                <Input
                  label="Enter Custom Monthly EMI"
                  type="number"
                  placeholder={emiAmount.toString()}
                  step="100"
                  value={customEMI}
                  onChange={(e) => setCustomEMI(e.target.value)}
                  hint={`Current EMI: ${formatCurrency(emiAmount)}`}
                  className="w-full"
                />

                {customEMI && customAnalysis && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="mt-4 space-y-3"
                  >
                    {customAnalysis.error ? (
                      <div className="p-3 bg-red-100 border border-red-300 rounded-lg text-red-800 text-sm break-words">
                        {customAnalysis.error}
                      </div>
                    ) : (
                      <>
                        <div className="p-3 bg-white dark:bg-gray-800 rounded-lg min-w-0 break-words">
                          <p className="text-sm-fluid text-gray-600 dark:text-gray-400">New Loan Tenure</p>
                          <p className="text-xl-fluid font-bold text-indigo-600 dark:text-indigo-400">
                            {customAnalysis.newMonths} months ({(customAnalysis.newMonths / 12).toFixed(1)} years)
                          </p>
                        </div>

                        <div className="p-3 bg-white dark:bg-gray-800 rounded-lg min-w-0 break-words">
                          <p className="text-sm-fluid text-gray-600 dark:text-gray-400">New Total Interest</p>
                          <p className="text-xl-fluid font-bold text-indigo-600 dark:text-indigo-400">
                            {formatCurrency(customAnalysis.newTotalInterest)}
                          </p>
                        </div>

                        {customAnalysis.saveMonths > 0 && (
                          <motion.div
                            initial={{ scale: 0.95 }}
                            animate={{ scale: 1 }}
                            className="p-4 bg-green-50 border-2 border-green-300 rounded-lg break-words"
                          >
                            <p className="text-sm-fluid font-semibold text-green-800 mb-2">💰 Savings Opportunity:</p>
                            <p className="text-green-700">
                              Save <span className="font-bold">{customAnalysis.saveMonths} months</span> and{' '}
                              <span className="font-bold">{formatCurrency(customAnalysis.saveMoney)}</span> in interest!
                            </p>
                          </motion.div>
                        )}

                        {customAnalysis.saveMonths === 0 && customAnalysis.saveMoney < 0 && (
                          <div className="p-4 bg-orange-50 border-2 border-orange-300 rounded-lg break-words">
                            <p className="text-sm font-semibold text-orange-800 mb-2">⚠️ Note:</p>
                            <p className="text-orange-700">
                              This EMI is lower than the current one, extending your loan term and increasing total interest.
                            </p>
                          </div>
                        )}
                      </>
                    )}
                  </motion.div>
                )}
              </Card>
            </motion.div>
          )}
        </motion.div>

        {/* Analysis Tools */}
        <motion.div
          className="space-y-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          {!showRateImpact && !showPrepayment && (
            <div className="grid grid-cols-2 gap-3">
              <Button
                onClick={() => setShowRateImpact(true)}
                variant="secondary"
                className="text-sm-fluid"
              >
                📊 Rate Impact Analysis
              </Button>
              <Button
                onClick={() => setShowPrepayment(true)}
                variant="secondary"
                className="text-sm-fluid"
              >
                ⚡ Prepayment Analysis
              </Button>
            </div>
          )}

          {showRateImpact && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <RateImpactAnalyzer loan={loan} currency="USD" />
              <Button
                onClick={() => setShowRateImpact(false)}
                variant="secondary"
                className="w-full mt-3"
              >
                Back to Details
              </Button>
            </motion.div>
          )}

          {showPrepayment && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <PrepaymentAnalyzer loan={loan} currency="USD" />
              <Button
                onClick={() => setShowPrepayment(false)}
                variant="secondary"
                className="w-full mt-3"
              >
                Back to Details
              </Button>
            </motion.div>
          )}
        </motion.div>

        {/* Help Section */}
        <Card className="p-4 bg-blue-50 dark:bg-blue-900/10 border-l-4 border-blue-400">
          <p className="text-sm-fluid text-gray-700 dark:text-gray-200">
            <span className="font-semibold dark:text-gray-100">💡 Formula:</span> EMI = P × r × (1+r)^n / ((1+r)^n - 1)
            <br />
            <span className="text-xs-fluid text-gray-600 dark:text-gray-400">
              Where P = Principal, r = Monthly Rate, n = Number of Months
            </span>
          </p>
        </Card>

        {/* Close Button */}
        <Button
          onClick={onClose}
          variant="secondary"
          className="w-full"
        >
          Close
        </Button>
      </motion.div>
    </div>
  )
}
