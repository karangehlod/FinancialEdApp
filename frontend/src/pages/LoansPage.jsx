import React, { useEffect } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import { Card, Button, LoadingSpinner, EmptyState, Input, Select, Modal } from '../components/UI'
import { useLoanStore } from '../store/index'
import { LoanAdvancedDetails } from '../components/loans/LoanAdvancedDetails'
import { EMISummaryCard } from '../components/loans/EMISummaryCard'
import { motion } from 'framer-motion'
import { Trash2, Edit2, Plus, BarChart3 } from 'lucide-react'
import { formatDate } from '../utils/helpers'
import { showSuccessToast, showErrorToast } from '../utils/toast'
import { useState } from 'react'

export const LoansPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency, currency } = useCurrency()
  const {
    loans,
    fetchLoans,
    addLoan,
    updateLoan,
    deleteLoan,
    isLoading: loansLoading,
  } = useLoanStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [detailsModalOpen, setDetailsModalOpen] = useState(false)
  const [selectedLoan, setSelectedLoan] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    loan_type: 'Personal',
    lender: '',
    amount: '',
    interest_rate: '',
    term_months: '',
    start_date: new Date().toISOString().split('T')[0],
  })
  const [formErrors, setFormErrors] = useState({})

  useEffect(() => {
    if (isAuthenticated) {
      fetchLoans()
    }
  }, [isAuthenticated])

  const validateForm = () => {
    const errors = {}
    if (!formData.lender) errors.lender = 'Lender name is required'
    if (!formData.amount) errors.amount = 'Loan amount is required'
    else if (parseFloat(formData.amount) <= 0) errors.amount = 'Amount must be positive'
    if (!formData.term_months) errors.term_months = 'Loan term is required'
    return errors
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    const errors = validateForm()

    if (Object.keys(errors).length > 0) {
      setFormErrors(errors)
      return
    }

    try {
      const data = {
        loan_type: formData.loan_type || 'Personal',
        lender_name: formData.lender,
        principal_amount: parseFloat(formData.amount),
        interest_rate: formData.interest_rate ? parseFloat(formData.interest_rate) : 0,
        loan_term_months: parseInt(formData.term_months),
        start_date: formData.start_date,
      }

      if (editingId) {
        await updateLoan(editingId, data)
        showSuccessToast('Loan updated successfully')
      } else {
        await addLoan(data)
        showSuccessToast('Loan added successfully')
      }
      setIsModalOpen(false)
      resetForm()
    } catch (err) {
      showErrorToast(editingId ? 'Failed to update loan' : 'Failed to add loan')
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this loan?')) {
      try {
        // logger.info('Deleting loan', { id })
        await deleteLoan(id)
        // logger.info('Loan deleted successfully', { id })
        showSuccessToast('Loan deleted successfully')
      } catch (err) {
        console.error('❌ Delete error:', err)
        showErrorToast(`Failed to delete loan: ${err?.message || 'Unknown error'}`)
      }
    }
  }

  const handleEdit = (loan) => {
    setEditingId(loan.id)
    setFormData({
      loan_type: loan.loan_type || 'Personal',
      lender: loan.lender_name || loan.lender || '',
      amount: (loan.principal_amount || loan.amount).toString(),
      interest_rate: loan.interest_rate ? loan.interest_rate.toString() : '',
      term_months: (loan.loan_term_months || loan.term_months).toString(),
      start_date: loan.start_date,
    })
    setIsModalOpen(true)
  }

  const resetForm = () => {
    setFormData({
      loan_type: 'Personal',
      lender: '',
      amount: '',
      interest_rate: '',
      term_months: '',
      start_date: new Date().toISOString().split('T')[0],
    })
    setFormErrors({})
    setEditingId(null)
  }

  const totalLoanAmount = loans.reduce((sum, loan) => sum + (parseFloat(loan.principal_amount || loan.amount || 0) || 0), 0)
  
  // Calculate total monthly EMI
  const calculateEMI = (principal, rate, months) => {
    if (months <= 0 || principal <= 0) return 0
    const monthlyRate = rate / 12 / 100
    if (monthlyRate === 0) return principal / months
    const numerator = monthlyRate * Math.pow(1 + monthlyRate, months)
    const denominator = Math.pow(1 + monthlyRate, months) - 1
    return principal * (numerator / denominator)
  }
  
  const totalMonthlyEMI = loans.reduce((sum, loan) => {
    const emi = loan.emi_amount ? parseFloat(loan.emi_amount) : calculateEMI(
      parseFloat(loan.principal_amount || loan.amount || 0),
      parseFloat(loan.interest_rate || 0),
      parseInt(loan.loan_term_months || loan.term_months || 0)
    )
    return sum + (emi || 0)
  }, 0)

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="" style={{ maxWidth: 'var(--content-max-width)' }}>
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageContainer
        title="Loans"
        subtitle="Track and manage your loans"
        icon={BarChart3}
        iconSize={'var(--page-icon-size)'}
        iconAlt="Loans"
        action={
          <Button
            onClick={() => {
              resetForm()
              setIsModalOpen(true)
            }}
            variant="primary"
            className="gap-2"
          >
            <Plus size={20} />
            Add Loan
          </Button>
        }
      >
        {/* Summary - Total Loan Amount Card */}
        {loans.length > 0 && (
          <motion.div
            className="mb-6 grid grid-cols-1 lg:grid-cols-3 gap-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            {/* Total Loan Amount */}
            <motion.div
              className="p-6 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-900/20 rounded-lg border-l-4 border-blue-500 shadow-sm"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
            >
              <p className="text-gray-600 dark:text-gray-400 text-sm mb-2">Total Loan Amount</p>
              <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{formatCurrency(totalLoanAmount)}</p>
              <p className="text-gray-600 dark:text-gray-400 text-sm mt-2">{loans.length} active loans</p>
            </motion.div>

            {/* EMI Summary Card - Takes 2 columns on large screens */}
            <motion.div
              className="lg:col-span-2"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
            >
              <EMISummaryCard loans={loans} currency={currency} />
            </motion.div>
          </motion.div>
        )}

        {/* Loans List */}
        {loansLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : loans.length === 0 ? (
          <EmptyState
            icon={Plus}
            title="No loans yet"
            description="Track your loans to manage debt effectively"
            action={
              <Button onClick={() => setIsModalOpen(true)} variant="primary">
                Add First Loan
              </Button>
            }
          />
        ) : (
          <motion.div className="space-y-4">
            {loans.map((loan, index) => (
              <motion.div
                key={loan.id}
                className="glass rounded-lg p-6 flex items-center justify-between hover:shadow-card-hover"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.05 }}
                whileHover={{ x: 5 }}
              >
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">{loan.lender_name || loan.lender || 'Unknown Lender'}</h3>
                  <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-3 text-sm">
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Amount</p>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{formatCurrency(loan.principal_amount || loan.amount || 0)}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Interest Rate</p>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{loan.interest_rate || 0}%</p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Term</p>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{loan.loan_term_months || loan.term_months || 0} months</p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Monthly EMI</p>
                      <p className="font-semibold text-purple-600 dark:text-purple-400">{formatCurrency(
                        loan.emi_amount ? parseFloat(loan.emi_amount) : calculateEMI(
                          parseFloat(loan.principal_amount || loan.amount || 0),
                          parseFloat(loan.interest_rate || 0),
                          parseInt(loan.loan_term_months || loan.term_months || 0)
                        )
                      )}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 dark:text-gray-400">Start Date</p>
                      <p className="font-semibold text-gray-900 dark:text-gray-100">{formatDate(loan.start_date)}</p>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <motion.button
                    onClick={() => {
                      setSelectedLoan(loan)
                      setDetailsModalOpen(true)
                    }}
                    className="p-2 hover:bg-indigo-50 rounded-lg text-indigo-600"
                    title="View Details"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <BarChart3 size={18} />
                  </motion.button>
                  <motion.button
                    onClick={() => handleEdit(loan)}
                    className="p-2 hover:bg-blue-50 rounded-lg text-blue-600"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Edit2 size={18} />
                  </motion.button>
                  <motion.button
                    onClick={() => handleDelete(loan.id)}
                    className="p-2 hover:bg-red-50 rounded-lg text-red-600"
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    <Trash2 size={18} />
                  </motion.button>
                </div>
              </motion.div>
            ))}
          </motion.div>
        )}
      </PageContainer>

      {/* Add/Edit Loan Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          resetForm()
        }}
        title={editingId ? 'Edit Loan' : 'Add Loan'}
        className="max-w-md"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Loan Type"
            value={formData.loan_type}
            onChange={(e) => setFormData({ ...formData, loan_type: e.target.value })}
            options={[
              { value: 'Personal', label: 'Personal' },
              { value: 'Home', label: 'Home' },
              { value: 'Car', label: 'Car' },
              { value: 'Education', label: 'Education' },
              { value: 'Business', label: 'Business' },
              { value: 'Credit Card', label: 'Credit Card' },
              { value: 'Other', label: 'Other' },
            ]}
          />

          <Input
            label="Lender Name"
            type="text"
            placeholder="Bank Name or Lender"
            value={formData.lender}
            onChange={(e) => {
              setFormData({ ...formData, lender: e.target.value })
              setFormErrors({ ...formErrors, lender: '' })
            }}
            error={formErrors.lender}
          />

          <Input
            label="Loan Amount"
            type="number"
            placeholder="50000.00"
            step="0.01"
            value={formData.amount}
            onChange={(e) => {
              setFormData({ ...formData, amount: e.target.value })
              setFormErrors({ ...formErrors, amount: '' })
            }}
            error={formErrors.amount}
          />

          <Input
            label="Interest Rate (%)"
            type="number"
            placeholder="5.5"
            step="0.01"
            value={formData.interest_rate}
            onChange={(e) => setFormData({ ...formData, interest_rate: e.target.value })}
          />

          <Input
            label="Loan Term (Months)"
            type="number"
            placeholder="60"
            value={formData.term_months}
            onChange={(e) => {
              setFormData({ ...formData, term_months: e.target.value })
              setFormErrors({ ...formErrors, term_months: '' })
            }}
            error={formErrors.term_months}
          />

          <Input
            label="Start Date"
            type="date"
            value={formData.start_date}
            onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
          />

          <div className="flex gap-3 pt-4">
            <Button
              type="submit"
              variant="primary"
              className="flex-1"
              isLoading={loansLoading}
            >
              {editingId ? 'Update' : 'Add'} Loan
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsModalOpen(false)
                resetForm()
              }}
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </form>
      </Modal>

      {/* Loan Details Modal */}
      <Modal
        isOpen={detailsModalOpen}
        onClose={() => {
          setDetailsModalOpen(false)
          setSelectedLoan(null)
        }}
        title={selectedLoan ? `${selectedLoan.lender_name || selectedLoan.lender || 'Loan'} - Details` : 'Loan Details'}
        className="max-w-2xl"
      >
        {selectedLoan && (
          <LoanAdvancedDetails
            loan={selectedLoan}
            onClose={() => {
              setDetailsModalOpen(false)
              setSelectedLoan(null)
            }}
          />
        )}
      </Modal>
    </Layout>
  )
}
