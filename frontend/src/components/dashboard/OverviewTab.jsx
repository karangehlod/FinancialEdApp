import React, { useMemo } from 'react'
import { Card, StatCard, EmptyState, Button } from '../UI'
import { MonthlySavingsTracker } from '../financial/MonthlySavingsTracker'
import { useProfileStore } from '../../store/index'
import { useCurrency } from '../../hooks/useCurrency'
import { motion } from 'framer-motion'
import {
  TrendingDown,
  PieChart as PieChartIcon,
  Target,
  Zap,
  Plus,
  TrendingUp,
  Wallet,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { 
  ExpenseDistributionChart,
  SpendingTrendChart,
} from './DashboardCharts'
import { DashboardDataService } from './DashboardDataService'

// Stats Overview Component
const StatsOverview = ({ stats, formatCurrency }) => {
  const statItems = [
    {
      icon: TrendingDown,
      label: 'Total Monthly Expenses',
      value: formatCurrency(stats.totalExpenses),
      color: 'red',
      subtext: `Includes ${formatCurrency(stats.totalEMI)} in loan EMI`,
    },
    {
      icon: Wallet,
      label: 'Total Budget Limit',
      value: formatCurrency(stats.totalBudgets),
      color: 'blue',
    },
    {
      icon: Target,
      label: 'Active Goals',
      value: stats.activeGoals,
      color: 'green',
    },
    {
      icon: Zap,
      label: 'Active Loans',
      value: stats.activeLoans,
      color: 'yellow',
    },
  ]

  return (
    <motion.div
      className="stats-grid gap-6 mb-8"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {statItems.map((item, index) => (
        <StatCard
          key={index}
          icon={item.icon}
          label={item.label}
          value={item.value}
          color={item.color}
          subtext={item.subtext}
        />
      ))}
    </motion.div>
  )
}

export const OverviewTab = ({ expenses = [], budgets = [], goals = [], loans = [] }) => {
  const navigate = useNavigate()
  const { financialProfile } = useProfileStore()
  const { formatCurrency, currency } = useCurrency()
  
  // Create data service instance
  const displayService = useMemo(
    () => new DashboardDataService(expenses, budgets, goals, loans),
    [expenses, budgets, goals, loans]
  )

  // Calculate derived data
  const displayStats = useMemo(() => displayService.getStatistics(), [displayService])
  const displayExpensesByCategory = useMemo(() => displayService.getExpensesByCategory(), [displayService])
  const displaySpendingData = useMemo(() => displayService.getLast30DaysSpending(), [displayService])

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      {/* Stats Overview */}
      <StatsOverview stats={displayStats} formatCurrency={formatCurrency} />

      {/* Monthly Savings Tracker */}
      {(financialProfile?.monthly_salary || 0) > 0 && (
        <motion.div
          className="mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
        >
          <MonthlySavingsTracker
            monthlyIncome={parseFloat(financialProfile?.monthly_salary || 0)}
            totalEMI={displayStats.totalEMI}
            totalBudget={displayStats.budgetAmount}
            currency={currency}
            isLoading={false}
          />
        </motion.div>
      )}

      {/* Charts Grid */}
      <motion.div
        className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        {/* Expense Distribution Pie Chart */}
        <Card>
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2 dark:text-gray-100">
            <PieChartIcon size={20} className="text-blue-600" />
            Expense Distribution
          </h3>
          <ExpenseDistributionChart data={displayExpensesByCategory} />
        </Card>

        {/* Spending Trend */}
        <Card>
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2 dark:text-gray-100">
            <TrendingUp size={20} className="text-green-600" />
            Spending Trend (Last 30 Days)
          </h3>
          <SpendingTrendChart data={displaySpendingData} viewType="30days" />
        </Card>
      </motion.div>

      {/* Quick Actions */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <Card 
          className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => navigate('/expenses')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Recent Transactions</p>
              <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{expenses.length}</p>
            </div>
            <TrendingDown size={32} className="text-blue-400" />
          </div>
        </Card>

        <Card 
          className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => navigate('/goals')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Goals in Progress</p>
              <p className="text-2xl font-bold text-green-600 dark:text-green-400">{displayStats.activeGoals}</p>
            </div>
            <Target size={32} className="text-green-400" />
          </div>
        </Card>

        <Card 
          className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30 cursor-pointer hover:shadow-lg transition-shadow"
          onClick={() => navigate('/budgets')}
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400">Budgets Setup</p>
              <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{budgets.length}</p>
            </div>
            <Wallet size={32} className="text-yellow-400" />
          </div>
        </Card>
      </motion.div>
    </motion.div>
  )
}
