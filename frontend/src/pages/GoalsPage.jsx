import React, { useEffect, useState } from 'react'
import { Layout, PageContainer } from '../components/Layout'
import { useProtectedRoute } from '../hooks/useAuth'
import { useCurrency } from '../hooks/useCurrency'
import {
  Card,
  Button,
  Input,
  LoadingSpinner,
  EmptyState,
  Modal,
  ProgressBar,
} from '../components/UI'
import { useGoalStore } from '../store/index'
import { GoalAllocationStrategy } from '../components/goals/GoalAllocationStrategy'
import { motion } from 'framer-motion'
import { Trash2, Edit2, Plus, Target, Zap } from 'lucide-react'
import { calculatePercentage } from '../utils/helpers'
import { showSuccessToast, showErrorToast } from '../utils/toast'

export const GoalsPage = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const {
    goals,
    fetchGoals,
    addGoal,
    updateGoal,
    addProgress,
    deleteGoal,
    isLoading: goalsLoading,
  } = useGoalStore()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false)
  const [strategyModalOpen, setStrategyModalOpen] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [progressAmount, setProgressAmount] = useState('')
  const [progressGoalId, setProgressGoalId] = useState(null)
  const [formData, setFormData] = useState({
    goal_name: '',
    description: '',
    goal_type: 'savings',
    target_amount: '',
    target_date: '',
    priority: 'medium',
  })
  const [formErrors, setFormErrors] = useState({})

  useEffect(() => {
    if (isAuthenticated) {
      fetchGoals()
    }
  }, [isAuthenticated])

  const validateForm = () => {
    const errors = {}
    if (!formData.goal_name) errors.goal_name = 'Goal name is required'
    if (!formData.goal_type) errors.goal_type = 'Goal type is required'
    if (!formData.target_amount) errors.target_amount = 'Target amount is required'
    else if (parseFloat(formData.target_amount) <= 0) errors.target_amount = 'Amount must be positive'
    if (!formData.target_date) errors.target_date = 'Target date is required'
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
        goal_name: formData.goal_name,
        description: formData.description,
        goal_type: formData.goal_type,
        target_amount: parseFloat(formData.target_amount),
        target_date: formData.target_date,
        priority: formData.priority,
      }

      if (editingId) {
        await updateGoal(editingId, data)
        showSuccessToast('Goal updated successfully')
      } else {
        await addGoal(data)
        showSuccessToast('Goal created successfully')
      }
      setIsModalOpen(false)
      resetForm()
    } catch (err) {
      showErrorToast(editingId ? 'Failed to update goal' : 'Failed to create goal')
    }
  }

  const handleAddProgress = async (e) => {
    e.preventDefault()
    if (!progressAmount || parseFloat(progressAmount) <= 0) {
      showErrorToast('Please enter a valid amount')
      return
    }

    try {
      await addProgress(progressGoalId, parseFloat(progressAmount))
      showSuccessToast('Progress added successfully')
      setIsProgressModalOpen(false)
      setProgressAmount('')
      setProgressGoalId(null)
    } catch (err) {
      showErrorToast('Failed to add progress')
    }
  }

  const handleDelete = async (id) => {
    if (window.confirm('Are you sure you want to delete this goal?')) {
      try {
        await deleteGoal(id)
        showSuccessToast('Goal deleted successfully')
      } catch (err) {
        showErrorToast('Failed to delete goal')
      }
    }
  }

  const handleEdit = (goal) => {
    setEditingId(goal.id)
    setFormData({
      goal_name: goal.goal_name || goal.name || '',
      description: goal.description || '',
      goal_type: goal.goal_type || 'savings',
      target_amount: goal.target_amount.toString(),
      target_date: goal.target_date || goal.deadline || '',
      priority: goal.priority || 'medium',
    })
    setIsModalOpen(true)
  }

  const resetForm = () => {
    setFormData({
      goal_name: '',
      description: '',
      goal_type: 'savings',
      target_amount: '',
      target_date: '',
      priority: 'medium',
    })
    setFormErrors({})
    setEditingId(null)
  }

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    )
  }

  const completedGoals = goals.filter((g) => g.status === 'completed').length
  const activeGoals = goals.filter((g) => g.status !== 'completed').length

  return (
    <Layout>
      <PageContainer
        title="Financial Goals"
        subtitle="Set and track your savings goals"
        icon={Target}
        iconSize={'var(--page-icon-size)'}
        iconAlt="Goals"
        action={
          <div className="flex gap-3">
            <Button
              onClick={() => {
                resetForm()
                setIsModalOpen(true)
              }}
              variant="primary"
              className="gap-2"
            >
              <Plus size={20} />
              New Goal
            </Button>
            <Button
              onClick={() => setStrategyModalOpen(true)}
              variant="secondary"
              className="gap-2"
            >
              <Zap size={20} />
              Allocation Strategy
            </Button>
          </div>
        }
      >
        {/* Stats */}
        <motion.div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Active Goals</p>
            <p className="text-3xl font-bold text-primary-600 dark:text-primary-400 mt-2">{activeGoals}</p>
          </Card>
          <Card>
            <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Completed Goals</p>
            <p className="text-3xl font-bold text-green-600 dark:text-green-400 mt-2">{completedGoals}</p>
          </Card>
          <Card>
            <p className="text-gray-600 dark:text-gray-400 text-sm font-medium">Total Goals</p>
            <p className="text-3xl font-bold text-secondary-600 dark:text-secondary-400 mt-2">{goals.length}</p>
          </Card>
        </motion.div>

        {/* Goals List */}
        {goalsLoading ? (
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        ) : goals.length === 0 ? (
          <EmptyState
            icon={Target}
            title="No goals yet"
            description="Create a financial goal to start saving"
            action={
              <Button onClick={() => setIsModalOpen(true)} variant="primary">
                Create First Goal
              </Button>
            }
          />
        ) : (
          <motion.div className="space-y-4">
            {goals.map((goal, index) => {
              const percentage = calculatePercentage(goal.current_amount, goal.target_amount)

              return (
                <motion.div
                  key={goal.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <Card className={goal.status === 'completed' ? 'bg-green-50 dark:bg-green-900/20' : ''}>
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">{goal.goal_name}</h3>
                        {goal.description && (
                          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">{goal.description}</p>
                        )}
                        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                          {formatCurrency(goal.current_amount)} / {formatCurrency(goal.target_amount)}
                        </p>
                      </div>
                      <div className="flex gap-2 flex-shrink-0">
                        {goal.status !== 'completed' && (
                          <motion.button
                            onClick={() => {
                              setProgressGoalId(goal.id)
                              setIsProgressModalOpen(true)
                            }}
                            className="px-3 py-2 bg-green-100 text-green-700 rounded-lg text-sm font-medium hover:bg-green-200"
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            Add Progress
                          </motion.button>
                        )}
                        {!goal.completed && (
                          <motion.button
                            onClick={() => handleEdit(goal)}
                            className="p-2 hover:bg-blue-50 rounded-lg text-blue-600"
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.95 }}
                          >
                            <Edit2 size={18} />
                          </motion.button>
                        )}
                        <motion.button
                          onClick={() => handleDelete(goal.id)}
                          className="p-2 hover:bg-red-50 rounded-lg text-red-600"
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.95 }}
                        >
                          <Trash2 size={18} />
                        </motion.button>
                      </div>
                    </div>

                    <ProgressBar
                      value={goal.current_amount}
                      max={goal.target_amount}
                      color={goal.completed ? 'success' : 'primary'}
                      showLabel={false}
                    />

                    <div className="flex items-center justify-between mt-4">
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {Math.min(Math.round(percentage), 100)}% completed
                      </p>
                      {goal.target_date && (
                        <p className="text-sm text-gray-500 dark:text-gray-400">
                          Due: {new Date(goal.target_date).toLocaleDateString()}
                        </p>
                      )}
                      {goal.status === 'completed' && (
                        <div className="px-3 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded-full">
                          ✓ Completed
                        </div>
                      )}
                    </div>
                  </Card>
                </motion.div>
              )
            })}
          </motion.div>
        )}
      </PageContainer>

      {/* Add/Edit Goal Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false)
          resetForm()
        }}
        title={editingId ? 'Edit Goal' : 'Create Goal'}
        className="max-w-md"
      >
        <form onSubmit={handleSubmit} className="space-y-4">
          <Input
            label="Goal Name"
            type="text"
            placeholder="e.g., Emergency Fund"
            value={formData.goal_name}
            onChange={(e) => {
              setFormData({ ...formData, goal_name: e.target.value })
              setFormErrors({ ...formErrors, goal_name: '' })
            }}
            error={formErrors.goal_name}
          />

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Goal Type</label>
            <select
              value={formData.goal_type}
              onChange={(e) => {
                setFormData({ ...formData, goal_type: e.target.value })
                setFormErrors({ ...formErrors, goal_type: '' })
              }}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="savings">Savings</option>
              <option value="debt_payoff">Debt Payoff</option>
              <option value="investment">Investment</option>
              <option value="emergency_fund">Emergency Fund</option>
              <option value="other">Other</option>
            </select>
            {formErrors.goal_type && <p className="text-sm text-red-600">{formErrors.goal_type}</p>}
          </div>

          <Input
            label="Description (Optional)"
            type="text"
            placeholder="e.g., For unexpected expenses"
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
          />

          <Input
            label="Target Amount"
            type="number"
            placeholder="5000.00"
            step="0.01"
            value={formData.target_amount}
            onChange={(e) => {
              setFormData({ ...formData, target_amount: e.target.value })
              setFormErrors({ ...formErrors, target_amount: '' })
            }}
            error={formErrors.target_amount}
          />

          <Input
            label="Target Date"
            type="date"
            value={formData.target_date}
            onChange={(e) => {
              setFormData({ ...formData, target_date: e.target.value })
              setFormErrors({ ...formErrors, target_date: '' })
            }}
            error={formErrors.target_date}
          />

          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">Priority</label>
            <select
              value={formData.priority}
              onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-600"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={goalsLoading}>
              {editingId ? 'Update' : 'Create'} Goal
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

      {/* Add Progress Modal */}
      <Modal
        isOpen={isProgressModalOpen}
        onClose={() => {
          setIsProgressModalOpen(false)
          setProgressAmount('')
          setProgressGoalId(null)
        }}
        title="Add Progress"
        className="max-w-sm"
      >
        <form onSubmit={handleAddProgress} className="space-y-4">
          <Input
            label="Amount to Add"
            type="number"
            placeholder="100.00"
            step="0.01"
            value={progressAmount}
            onChange={(e) => setProgressAmount(e.target.value)}
          />

          <div className="flex gap-3 pt-4">
            <Button type="submit" variant="primary" className="flex-1" isLoading={goalsLoading}>
              Add Progress
            </Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setIsProgressModalOpen(false)
                setProgressAmount('')
                setProgressGoalId(null)
              }}
              className="flex-1"
            >
              Cancel
            </Button>
          </div>
        </form>
      </Modal>

      {/* Goal Allocation Strategy Modal */}
      <Modal
        isOpen={strategyModalOpen}
        onClose={() => setStrategyModalOpen(false)}
        title="Goal Allocation Strategy"
        className="max-w-3xl max-h-[90vh] overflow-y-auto"
      >
        <GoalAllocationStrategy
          goals={goals}
          monthlyAvailable={0}
          onClose={() => setStrategyModalOpen(false)}
        />
      </Modal>
    </Layout>
  )
}
