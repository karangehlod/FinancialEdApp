import React, { useMemo } from 'react'
import { Card, EmptyState, Button } from '../UI'
import { motion } from 'framer-motion'
import { Target } from 'lucide-react'
import { formatCurrency } from '../../utils/helpers'
import { useNavigate } from 'react-router-dom'
import { DashboardDataService } from './DashboardDataService'

// Goals Progress Chart Component
const GoalsProgressChart = ({ data }) => {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400">
        <p>No goal data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {data.map((goal, index) => (
        <motion.div
          key={goal.name}
          className="p-4 bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-900/20 dark:to-blue-900/20 rounded-lg border border-green-100 dark:border-green-800"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.1 }}
        >
          <div className="flex items-center justify-between mb-2">
            <p className="font-semibold text-gray-900 dark:text-gray-100">{goal.name}</p>
            <p className="text-sm font-bold text-green-600 dark:text-green-400">{goal.percentage.toFixed(1)}%</p>
          </div>
          <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
            <motion.div
              className="bg-gradient-to-r from-green-400 to-blue-500 h-3 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${goal.percentage}%` }}
              transition={{ duration: 0.8, ease: 'easeOut' }}
            />
          </div>
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-2">
            {formatCurrency(goal.current)} of {formatCurrency(goal.target)}
          </p>
        </motion.div>
      ))}
    </div>
  )
}

export const GoalsTab = ({ goals = [] }) => {
  const navigate = useNavigate()
  
  // Create data service instance for goal calculations
  const displayService = useMemo(
    () => new DashboardDataService([], [], goals, []),
    [goals]
  )
  
  const displayGoalProgress = useMemo(
    () => displayService.getGoalProgress(),
    [displayService]
  )

  if (goals.length === 0) {
    return (
      <EmptyState
        icon={Target}
        title="No Goals Yet"
        description="Set financial goals to track your progress"
        action={
          <Button onClick={() => navigate('/goals')} variant="primary">
            Create Goal
          </Button>
        }
      />
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="mb-4 flex justify-between items-center">
        <h3 className="text-lg font-bold">Goals Progress</h3>
        <Button onClick={() => navigate('/goals')} variant="primary" size="sm">
          Manage Goals
        </Button>
      </div>
      
      <Card>
        <GoalsProgressChart data={displayGoalProgress} />
      </Card>
    </motion.div>
  )
}
