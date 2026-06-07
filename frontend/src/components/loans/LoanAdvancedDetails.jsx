import React, { useState, useMemo, useEffect } from 'react'
import { Card, Button, Input, Modal } from '../UI'
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
 * where:
 *   P = Principal amount
 *   r = Monthly interest rate (annual_rate / 12 / 100)
 *   n = Number of months
 */
const calculateEMI = (principal, annualRate, months) => {
  if (months <= 0 || principal <= 0) return 0
  
  const monthlyRate = annualRate / 12 / 100
  
  if (monthlyRate === 0) {
    // No interest - simple division
    return principal / months
  }
  
  const numerator = monthlyRate * Math.pow(1 + monthlyRate, months)
  const denominator = Math.pow(1 + monthlyRate, months) - 1
  const emi = principal * (numerator / denominator)
  
  return Math.round(emi * 100) / 100
}

/**
 * Calculate total interest paid over the loan term
 */
const calculateTotalInterest = (principal, emi, months) => {
  const totalPaid = emi * months
  return Math.round((totalPaid - principal) * 100) / 100
}

/**
 * Calculate end date of the loan
 */
const calculateEndDate = (startDate, months) => {
  const date = new Date(startDate)
  date.setMonth(date.getMonth() + months)
  return date
}

/**
 * Calculate remaining months based on start date and total term
 */
const calculateRemainingMonths = (startDate, totalMonths) => {
  const start = new Date(startDate)
  const today = new Date()
  
  const endDate = new Date(start)
  endDate.setMonth(endDate.getMonth() + totalMonths)
  
  const monthsDifference = (today.getFullYear() - start.getFullYear()) * 12 + 
                          (today.getMonth() - start.getMonth())
  
  const remaining = totalMonths - Math.max(0, monthsDifference)
  return Math.max(0, remaining)
}

/**
 * LoanAdvancedDetails Component
 * Displays detailed EMI calculations, loan timeline, and interest breakdown
 */
export const LoanAdvancedDetails = ({ loan, onClose }) => {
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

   const principal = parseFloat(loan.principal_amount || loan.amount || 0)
   const annualRate = parseFloat(loan.interest_rate || 0)
   const months = parseInt(loan.loan_term_months || loan.term_months || 0)

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
  }, [loan && loan.id])

   // Calculate EMI
   const emiAmount = loan.emi_amount 
     ? parseFloat(loan.emi_amount) 
     : calculateEMI(principal, annualRate, months)

   // Calculate derived values
   const totalInterest = calculateTotalInterest(principal, emiAmount, months)
   const totalAmount = principal + totalInterest
   const endDate = calculateEndDate(loan.start_date, months)
   // Prefer backend remaining months/payments when available
   const remainingMonthsFromBackend = remoteLoan?.payments_remaining ?? remoteLoan?.remaining_months
   const remainingMonthsFromSchedule = remoteSchedule ? remoteSchedule.filter((s) => !s.is_paid).length : null
   const remainingMonths = remainingMonthsFromBackend ?? remainingMonthsFromSchedule ?? calculateRemainingMonths(loan.start_date, months)

   // Outstanding principal (backend authoritative if available)
   const outstandingBalance = (() => {
     const remoteOutstanding = remoteLoan?.remaining_principal ?? remoteLoan?.outstanding_balance
     if (remoteOutstanding !== undefined && remoteOutstanding !== null) return parseFloat(remoteOutstanding)
     if (loan.outstanding_balance !== undefined && loan.outstanding_balance !== null) return parseFloat(loan.outstanding_balance)
     return principal
   })()

   // Custom EMI analysis
   const customEMIValue = customEMI ? parseFloat(customEMI) : null
   const customAnalysis = useMemo(() => {
     if (!customEMIValue || customEMIValue <= 0) return null

    // Calculate new tenure: n = log(EMI / (EMI - P*r)) / log(1+r)
    const monthlyRate = annualRate / 12 / 100
    
    if (monthlyRate === 0) {
      // No interest - simple calculation
      const newMonths = Math.ceil(principal / customEMIValue)
      const newTotalInterest = 0
      return {
        newMonths,
        newTotalInterest,
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

    // Using logarithm formula
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
  const emiToIncomeRatio = loan.monthly_income 
    ? ((emiAmount / parseFloat(loan.monthly_income)) * 100).toFixed(2)
    : null

  const startDateDisplay = remoteLoan?.start_date || loan?.start_date

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

    // Prevent choosing a future date
    const selected = new Date(newStartDate)
    const today = new Date()
    // normalize both to YYYY-MM-DD
    const selISO = selected.toISOString().slice(0, 10)
    const todayISO = today.toISOString().slice(0, 10)
    if (selISO > todayISO) {
      showErrorToast('Start date cannot be in the future')
      return
    }

    // Normalize date string to YYYY-MM-DD
    const normalized = selISO
    setSavingStartDate(true)
    try {
      const updated = await loanService.update(loan.id, { start_date: normalized })
      // Refresh remote data
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

  // ...existing code...
  return (
    <motion.div
      className="space-y-6 text-gray-900 dark:text-gray-100 max-w-full min-w-0"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 overflow-x-auto">
        {/* EMI */}
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-800/20">
          <div className="flex items-start justify-between min-w-0">
            <div className="min-w-0">
              <p className="text-xs text-gray-600 mb-1 truncate">Monthly EMI</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400 truncate">{formatCurrency(emiAmount)}</p>
            </div>
            <DollarSign size={20} className="text-blue-600 opacity-60" />
          </div>
        </Card>

        {/* Outstanding Principal (backend when available) */}
        <Card className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/20 dark:to-orange-800/20">
          <div className="flex items-start justify-between min-w-0">
            <div className="min-w-0">
              <p className="text-xs text-gray-600 mb-1 truncate">Outstanding Principal</p>
              <p className="text-2xl font-bold text-orange-600 dark:text-orange-400 truncate">{formatCurrency(outstandingBalance)}</p>
              {remoteLoan && (
                <p className="text-xs text-gray-500 mt-1 truncate">(Updated from server)</p>
              )}
            </div>
            <TrendingDown size={20} className="text-orange-600 opacity-60" />
          </div>
        </Card>

        {/* End Date */}
        <Card className="p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-800/20">
           <div className="flex items-start justify-between min-w-0">
             <div className="min-w-0">
               <p className="text-xs text-gray-600 mb-1 truncate">End Date</p>
               <div className="flex items-center gap-3 min-w-0">
                 <p className="text-sm font-bold text-green-600 dark:text-green-400 truncate">{formatDate(endDate)}</p>
                 {/* Edit start date control */}
                 {!editingStartDate ? (
                   <button
                     onClick={handleEditStartDate}
                     className="text-xs text-indigo-600 hover:underline"
                     title="Edit loan start date"
                   >
                     Edit start date
                   </button>
                 ) : (
                   <div className="flex items-center gap-2 min-w-0">
                     <input
                       type="date"
                       value={newStartDate ? newStartDate.slice(0,10) : ''}
                       onChange={(e) => setNewStartDate(e.target.value)}
                       max={new Date().toISOString().slice(0,10)}
                       className="text-sm p-1 border rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 border-gray-300 dark:border-gray-600 focus:outline-none"
                     />
                     <button onClick={handleSaveStartDate} disabled={savingStartDate} className="text-xs text-green-600 font-semibold">{savingStartDate ? 'Saving...' : 'Save'}</button>
                     <button onClick={handleCancelEdit} className="text-xs text-gray-500">Cancel</button>
                   </div>
                 )}
               </div>
             </div>
             <Calendar size={20} className="text-green-600 opacity-60" />
           </div>
         </Card>

         {/* Remaining Months */}
         <Card className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-800/20">
           <div className="flex items-start justify-between min-w-0">
             <div className="min-w-0">
               <p className="text-xs text-gray-600 mb-1 truncate">Remaining</p>
               <p className="text-2xl font-bold text-purple-600 dark:text-purple-400 truncate">{remainingMonths}</p>
               <p className="text-xs text-gray-500 truncate">months</p>
             </div>
             <Clock size={20} className="text-purple-600 opacity-60" />
           </div>
         </Card>
      </div>

      {/* Summary Section */}
      <Card className="p-6 bg-gradient-to-r from-slate-50 to-slate-100 dark:from-slate-800 dark:to-slate-900 border-l-4 border-slate-400 dark:border-slate-700">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Loan Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div className="min-w-0 break-words">
            <p className="text-gray-600 dark:text-gray-400">Principal Amount</p>
            <p className="font-bold text-gray-900 dark:text-gray-100 truncate">{formatCurrency(principal)}</p>
          </div>
          <div className="min-w-0 break-words">
            <p className="text-gray-600 dark:text-gray-400">Total Amount (P + I)</p>
            <p className="font-bold text-gray-900 dark:text-gray-100 truncate">{formatCurrency(totalAmount)}</p>
          </div>
          <div className="min-w-0 break-words">
            <p className="text-gray-600 dark:text-gray-400">Total Loan Tenure</p>
            <p className="font-bold text-gray-900 dark:text-gray-100">{months} months</p>
          </div>
          <div className="min-w-0 break-words">
            <p className="text-gray-600 dark:text-gray-400">Annual Interest Rate</p>
            <p className="font-bold text-gray-900 dark:text-gray-100">{annualRate}%</p>
          </div>
          <div className="min-w-0 break-words">
            <p className="text-gray-600 dark:text-gray-400">Monthly Interest Rate</p>
            <p className="font-bold text-gray-900 dark:text-gray-100">{monthlyRate}%</p>
          </div>
          {emiToIncomeRatio && (
            <div className="min-w-0 break-words">
              <p className="text-gray-600 dark:text-gray-400">EMI to Income Ratio</p>
              <p className="font-bold text-gray-900 dark:text-gray-100">{emiToIncomeRatio}%</p>
            </div>
          )}
        </div>
      </Card>

      {/* Breakdown Section */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Payment Breakdown</h3>
        <div className="space-y-3">
          <div className="flex justify-between items-center p-3 bg-blue-50 dark:bg-blue-900/10 rounded-lg min-w-0">
            <span className="text-gray-700 dark:text-gray-200 truncate">Monthly Payment (EMI)</span>
            <span className="font-bold text-blue-600 dark:text-blue-400 truncate">{formatCurrency(emiAmount)}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-orange-50 dark:bg-orange-900/10 rounded-lg min-w-0">
            <span className="text-gray-700 dark:text-gray-200 truncate">Total Interest Over {months} months</span>
            <span className="font-bold text-orange-600 dark:text-orange-400 truncate">{formatCurrency(totalInterest)}</span>
          </div>
          <div className="flex justify-between items-center p-3 bg-green-50 dark:bg-green-900/10 rounded-lg min-w-0">
            <span className="text-gray-700 dark:text-gray-200 truncate">Total Amount to Pay</span>
            <span className="font-bold text-green-600 dark:text-green-400 truncate">{formatCurrency(totalAmount)}</span>
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
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Custom EMI Scenario</h3>
              <p className="text-sm text-gray-600 mb-4">
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
                        <p className="text-sm text-gray-600 dark:text-gray-400">New Loan Tenure</p>
                        <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                          {customAnalysis.newMonths} months ({(customAnalysis.newMonths / 12).toFixed(1)} years)
                        </p>
                      </div>

                      <div className="p-3 bg-white dark:bg-gray-800 rounded-lg min-w-0 break-words">
                        <p className="text-sm text-gray-600 dark:text-gray-400">New Total Interest</p>
                        <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                          {formatCurrency(customAnalysis.newTotalInterest)}
                        </p>
                      </div>

                      {customAnalysis.saveMonths > 0 && (
                        <motion.div
                          initial={{ scale: 0.95 }}
                          animate={{ scale: 1 }}
                          className="p-4 bg-green-50 border-2 border-green-300 rounded-lg break-words"
                        >
                          <p className="text-sm font-semibold text-green-800 mb-2">💰 Savings Opportunity:</p>
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
        {/* Rate Impact Analyzer Toggle */}
        {!showRateImpact && !showPrepayment && (
          <div className="grid grid-cols-2 gap-3">
            <Button
              onClick={() => setShowRateImpact(true)}
              variant="secondary"
              className="text-sm"
            >
              📊 Rate Impact Analysis
            </Button>
            <Button
              onClick={() => setShowPrepayment(true)}
              variant="secondary"
              className="text-sm"
            >
              ⚡ Prepayment Analysis
            </Button>
          </div>
        )}

        {/* Rate Impact Analyzer */}
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

        {/* Prepayment Analyzer */}
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
      <Card className="p-4 bg-blue-50 dark:bg-blue-900/10 border-l-4 border-blue-400 dark:border-blue-700">
        <p className="text-sm text-gray-700 dark:text-gray-200">
          <span className="font-semibold dark:text-gray-100">💡 Formula:</span> EMI = P × r × (1+r)^n / ((1+r)^n - 1)
          <br />
          <span className="text-xs text-gray-600 dark:text-gray-400">
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
  )
}
