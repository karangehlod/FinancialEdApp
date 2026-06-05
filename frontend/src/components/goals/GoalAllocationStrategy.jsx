import React, { useState, useMemo } from 'react'
import { Card, Button, Input, Select, FluidIcon } from '../UI'
import { motion } from 'framer-motion'
import { Target, TrendingUp, Zap, Calendar } from 'lucide-react'
import { formatCurrency, formatDate } from '../../utils/helpers'

/**
 * Calculate days remaining until goal target date
 */
const calculateDaysRemaining = (targetDate) => {
  const today = new Date()
  const target = new Date(targetDate)
  const diffTime = target - today
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return Math.max(0, diffDays)
}

/**
 * Calculate months remaining
 */
const calculateMonthsRemaining = (targetDate) => {
  const today = new Date()
  const target = new Date(targetDate)
  const months = (target.getFullYear() - today.getFullYear()) * 12 + 
                 (target.getMonth() - today.getMonth())
  return Math.max(0, months)
}

/**
 * Calculate required monthly contribution
 */
const calculateMonthlyContribution = (targetAmount, currentAmount, monthsRemaining) => {
  if (monthsRemaining <= 0) return 0
  const remaining = targetAmount - currentAmount
  return Math.max(0, remaining / monthsRemaining)
}

/**
 * Allocate funds based on strategy
 */
const allocateFunds = (availableFunds, goals, strategy) => {
  if (goals.length === 0) return {}

  const allocation = {}

  if (strategy === 'equal') {
    // Equal distribution
    const perGoal = availableFunds / goals.length
    goals.forEach(goal => {
      allocation[goal.id] = Math.round(perGoal * 100) / 100
    })
  } else if (strategy === 'priority') {
    // Priority-based: high priority gets 50%, medium 30%, low 20%
    const priorityWeights = {
      high: 0.5,
      medium: 0.3,
      low: 0.2,
    }

    const totalWeight = goals.reduce((sum, goal) => {
      return sum + (priorityWeights[goal.priority] || 0.2)
    }, 0)

    goals.forEach(goal => {
      const weight = priorityWeights[goal.priority] || 0.2
      allocation[goal.id] = Math.round((availableFunds * (weight / totalWeight)) * 100) / 100
    })
  } else if (strategy === 'urgency') {
    // Urgency-based: goals with sooner target dates get more funds
    const urgencies = goals.map(goal => ({
      id: goal.id,
      daysLeft: calculateDaysRemaining(goal.target_date),
    }))

    const totalUrgency = urgencies.reduce((sum, u) => sum + (1 / Math.max(u.daysLeft, 1)), 0)

    urgencies.forEach(u => {
      const weight = (1 / Math.max(u.daysLeft, 1)) / totalUrgency
      allocation[u.id] = Math.round((availableFunds * weight) * 100) / 100
    })
  } else if (strategy === 'proportional') {
    // Proportional to gap: goals further from target get more
    const gaps = goals.map(goal => ({
      id: goal.id,
      gap: Math.max(0, goal.target_amount - goal.current_amount),
    }))

    const totalGap = gaps.reduce((sum, g) => sum + g.gap, 0)

    if (totalGap > 0) {
      gaps.forEach(g => {
        const weight = g.gap / totalGap
        allocation[g.id] = Math.round((availableFunds * weight) * 100) / 100
      })
    } else {
      // All goals complete - distribute equally
      const perGoal = availableFunds / goals.length
      goals.forEach(goal => {
        allocation[goal.id] = Math.round(perGoal * 100) / 100
      })
    }
  }

  return allocation
}

/**
 * GoalAllocationStrategy Component
 * Displays goal allocation strategies, progress, and projections
 */
export const GoalAllocationStrategy = ({ goals = [], monthlyAvailable = 0, onClose }) => {
  const [selectedStrategy, setSelectedStrategy] = useState('priority')
  const [customMonthly, setCustomMonthly] = useState(monthlyAvailable.toString())
  const [showProjection, setShowProjection] = useState(false)

  const availableFunds = customMonthly ? parseFloat(customMonthly) : monthlyAvailable
  const allocation = allocateFunds(availableFunds, goals, selectedStrategy)

  // Calculate statistics
  const stats = useMemo(() => {
    const total = {
      target: 0,
      current: 0,
      progress: 0,
      remaining: 0,
      monthsAverage: 0,
      daysAverage: 0,
    }

    let goalCount = 0

    goals.forEach(goal => {
      total.target += parseFloat(goal.target_amount || 0)
      total.current += parseFloat(goal.current_amount || 0)
      total.remaining += Math.max(0, parseFloat(goal.target_amount || 0) - parseFloat(goal.current_amount || 0))
      total.monthsAverage += calculateMonthsRemaining(goal.target_date)
      total.daysAverage += calculateDaysRemaining(goal.target_date)
      goalCount++
    })

    if (goalCount > 0) {
      total.progress = (total.current / total.target) * 100 || 0
      total.monthsAverage = Math.round(total.monthsAverage / goalCount)
      total.daysAverage = Math.round(total.daysAverage / goalCount)
    }

    return total
  }, [goals])

  const strategyInfo = {
    priority: {
      name: 'Priority-Based',
      description: 'High priority goals get 50%, medium 30%, low 20%',
      icon: '⚡',
    },
    equal: {
      name: 'Equal Distribution',
      description: 'All goals get equal allocation regardless of priority',
      icon: '⚖️',
    },
    urgency: {
      name: 'Urgency-Based',
      description: 'Goals with sooner target dates get more funds',
      icon: '⏰',
    },
    proportional: {
      name: 'Gap-Based',
      description: 'Goals further from target amount get more funds',
      icon: '📊',
    },
  }

  const projections = useMemo(() => {
    if (!showProjection || !availableFunds) return {}

    const proj = {}
    goals.forEach(goal => {
      const monthlyAllocation = allocation[goal.id] || 0
      const remaining = Math.max(0, goal.target_amount - goal.current_amount)
      const monthsNeeded = monthlyAllocation > 0 ? Math.ceil(remaining / monthlyAllocation) : Infinity
      
      const projectedDate = new Date()
      projectedDate.setMonth(projectedDate.getMonth() + monthsNeeded)

      proj[goal.id] = {
        monthlyAllocation,
        monthsToComplete: monthsNeeded === Infinity ? 'Never' : monthsNeeded,
        projectedCompletionDate: monthsNeeded === Infinity ? null : projectedDate,
        canAchieve: monthsNeeded !== Infinity && monthsNeeded > 0,
      }
    })

    return proj
  }, [goals, allocation, showProjection, availableFunds])

  return (
    <motion.div
      className="space-y-6"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
    >
      {/* Overview Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30">
          <p className="text-xs-fluid text-gray-600 dark:text-gray-400 mb-1">Total Goals</p>
          <p className="text-stat font-bold text-blue-600 dark:text-blue-400">{goals.length}</p>
        </Card>

        <Card className="p-4 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30">
          <p className="text-xs-fluid text-gray-600 dark:text-gray-400 mb-1">Overall Progress</p>
          <p className="text-stat font-bold text-green-600 dark:text-green-400">{stats.progress.toFixed(1)}%</p>
        </Card>

        <Card className="p-4 bg-gradient-to-br from-orange-50 to-orange-100 dark:from-orange-900/30 dark:to-orange-800/30">
          <p className="text-xs-fluid text-gray-600 dark:text-gray-400 mb-1">Total Remaining</p>
          <p className="text-value font-bold text-orange-600 dark:text-orange-400">{formatCurrency(stats.remaining)}</p>
        </Card>

        <Card className="p-4 bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/30 dark:to-purple-800/30">
          <p className="text-xs-fluid text-gray-600 dark:text-gray-400 mb-1">Monthly Available</p>
          <p className="text-value font-bold text-purple-600 dark:text-purple-400">{formatCurrency(availableFunds)}</p>
        </Card>
      </div>

      {/* Strategy Selector */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Allocation Strategy</h3>
        <Select
          label="Choose Strategy"
          value={selectedStrategy}
          onChange={(e) => setSelectedStrategy(e.target.value)}
          options={[
            { value: 'priority', label: '⚡ Priority-Based (High: 50%, Medium: 30%, Low: 20%)' },
            { value: 'equal', label: '⚖️ Equal Distribution' },
            { value: 'urgency', label: '⏰ Urgency-Based (By Target Date)' },
            { value: 'proportional', label: '📊 Gap-Based (By Remaining Amount)' },
          ]}
        />
        <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-3">
          {strategyInfo[selectedStrategy]?.icon} {strategyInfo[selectedStrategy]?.description}
        </p>
      </Card>

      {/* Monthly Budget Input */}
      <Card className="p-6 bg-gradient-to-br from-indigo-50 to-indigo-100 dark:from-indigo-900/30 dark:to-indigo-800/30">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Monthly Budget</h3>
        <Input
          label="Available for Goals (Monthly)"
          type="number"
          step="100"
          value={customMonthly}
          onChange={(e) => setCustomMonthly(e.target.value)}
          hint="Enter your monthly disposable income for goals"
        />
      </Card>

      {/* Goals Allocation */}
      {goals.length > 0 ? (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Goal Allocation</h3>
          {goals.map((goal, index) => {
            const progress = (goal.current_amount / goal.target_amount) * 100
            const monthlyAllocation = allocation[goal.id] || 0
            const monthsNeeded = monthlyAllocation > 0 
              ? Math.ceil((goal.target_amount - goal.current_amount) / monthlyAllocation)
              : 0
            const daysRemaining = calculateDaysRemaining(goal.target_date)
            const monthsRemaining = calculateMonthsRemaining(goal.target_date)

            const projection = projections[goal.id]

            return (
              <motion.div
                key={goal.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <Card className="p-6">
                  {/* Goal Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex-1">
                      <h4 className="text-lg-fluid font-semibold text-gray-900 dark:text-gray-100">{goal.goal_name}</h4>
                      <p className="text-sm-fluid text-gray-600 dark:text-gray-400 mt-1">
                        Target: {formatCurrency(goal.target_amount)} | Current: {formatCurrency(goal.current_amount)}
                      </p>
                    </div>
                    <div className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      goal.priority === 'high' ? 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-400' :
                      goal.priority === 'medium' ? 'bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400' :
                      'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400'
                    }`}>
                      {goal.priority?.charAt(0).toUpperCase() + goal.priority?.slice(1)} Priority
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="mb-4">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-sm text-gray-600 dark:text-gray-400">Progress</span>
                      <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">{progress.toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-blue-500 to-indigo-600"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min(progress, 100)}%` }}
                        transition={{ duration: 1, ease: 'easeOut' }}
                      />
                    </div>
                  </div>

                  {/* Allocation Details Grid */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm-fluid mb-4">
                    <div className="bg-blue-50 dark:bg-blue-900/30 p-3 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400 text-xs-fluid">Monthly Allocation</p>
                      <p className="font-bold text-blue-600 dark:text-blue-400">{formatCurrency(monthlyAllocation)}</p>
                    </div>

                    <div className="bg-green-50 dark:bg-green-900/30 p-3 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400 text-xs-fluid">Allocation %</p>
                      <p className="font-bold text-green-600 dark:text-green-400">
                        {availableFunds > 0 ? ((monthlyAllocation / availableFunds) * 100).toFixed(1) : 0}%
                      </p>
                    </div>

                    <div className="bg-orange-50 dark:bg-orange-900/30 p-3 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400 text-xs-fluid">Months Remaining</p>
                      <p className="font-bold text-orange-600 dark:text-orange-400">{monthsRemaining}</p>
                    </div>

                    <div className="bg-purple-50 dark:bg-purple-900/30 p-3 rounded-lg">
                      <p className="text-gray-600 dark:text-gray-400 text-xs-fluid">Target Date</p>
                      <p className="font-bold text-purple-600 dark:text-purple-400 text-xs-fluid">{formatDate(goal.target_date)}</p>
                    </div>
                  </div>

                  {/* Feasibility Check */}
                  {monthsRemaining >= 0 && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className={`p-3 rounded-lg text-sm-fluid ${
                        monthlyAllocation > 0 && monthsNeeded <= monthsRemaining
                          ? 'bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-400'
                          : monthlyAllocation > 0
                          ? 'bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-400'
                          : 'bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-700 dark:text-gray-400'
                      }`}
                    >
                      {monthlyAllocation > 0 ? (
                        monthsNeeded <= monthsRemaining ? (
                          <span>
                            ✅ <strong>Achievable:</strong> Need {monthsNeeded} months, you have {monthsRemaining} months
                          </span>
                        ) : (
                          <span>
                            ⚠️ <strong>Tight Timeline:</strong> Need {monthsNeeded} months, but only {monthsRemaining} months available
                          </span>
                        )
                      ) : (
                        <span>
                          💡 Set a monthly allocation to see feasibility
                        </span>
                      )}
                    </motion.div>
                  )}
                </Card>
              </motion.div>
            )
          })}
        </div>
      ) : (
        <Card className="p-8 text-center bg-gray-50 dark:bg-gray-700">
          <FluidIcon icon={Target} size="lg" className="mx-auto text-gray-400 mb-3" />
           <p className="text-gray-600 dark:text-gray-400">No goals yet. Create goals to see allocation strategy.</p>
         </Card>
       )}

      {/* Projection Section */}
      {goals.length > 0 && (
        <>
          <Button
            onClick={() => setShowProjection(!showProjection)}
            variant="secondary"
            className="w-full"
          >
            {showProjection ? '✕ Hide Projections' : '+ Show Projections'}
          </Button>

          {showProjection && availableFunds > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-4"
            >
              <Card className="p-6 bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Projected Timeline</h3>
                <div className="space-y-3">
                  {goals.map(goal => {
                    const proj = projections[goal.id]
                    return (
                      <div key={goal.id} className="p-4 bg-white dark:bg-gray-800 rounded-lg border-l-4 border-green-500">
                        <p className="font-semibold text-gray-900 dark:text-gray-100">{goal.goal_name}</p>
                        <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                          <div>
                            <p className="text-gray-600 dark:text-gray-400">Monthly Allocation</p>
                            <p className="font-bold text-green-600 dark:text-green-400">{formatCurrency(proj?.monthlyAllocation || 0)}</p>
                          </div>
                          <div>
                            <p className="text-gray-600 dark:text-gray-400">Months to Complete</p>
                            <p className="font-bold text-green-600 dark:text-green-400">{proj?.monthsToComplete}</p>
                          </div>
                          {proj?.canAchieve && (
                            <div>
                              <p className="text-gray-600 dark:text-gray-400">Projected Completion</p>
                              <p className="font-bold text-green-600 dark:text-green-400">{formatDate(proj?.projectedCompletionDate)}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </Card>
            </motion.div>
          )}
        </>
      )}

      {/* Info Section */}
      <Card className="p-4 bg-blue-50 dark:bg-blue-900/30 border-l-4 border-blue-400">
        <p className="text-sm text-gray-700 dark:text-gray-300">
          <span className="font-semibold">💡 Strategy Guide:</span>
          <br />
          • <strong>Priority:</strong> Focus on high-priority goals first
          <br />
          • <strong>Equal:</strong> Fair distribution across all goals
          <br />
          • <strong>Urgency:</strong> Complete goals with sooner deadlines
          <br />
          • <strong>Gap-Based:</strong> Prioritize goals furthest from target
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
