import React, { useMemo, useState } from 'react'
import { Card, ProgressBar } from '../UI'
import { MonthlySavingsTracker } from '../financial/MonthlySavingsTracker'
import { useProfileStore } from '../../store/index'
import { useCurrency } from '../../hooks/useCurrency'
import { motion } from 'framer-motion'
import { TrendingDown, Target, Zap, Wallet } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { ExpenseDistributionChart, SpendingTrendChart, BudgetUtilizationChart } from './DashboardCharts'
import { DashboardDataService } from './DashboardDataService'
import { FluidGrid } from '../FluidGrid'
import { StatCard } from '../StatCard'
import { ChartGuard } from './ChartGuard'

interface OverviewTabProps {
  expenses?: any[]
  budgets?: any[]
  goals?: any[]
  loans?: any[]
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ expenses = [], budgets = [], goals = [], loans = [] }) => {
  const navigate = useNavigate()
  const { financialProfile } = useProfileStore()
  const { formatCurrency, currency } = useCurrency()

  const displayService = useMemo(() => new DashboardDataService(expenses, budgets, goals, loans), [expenses, budgets, goals, loans])

  const displayStats = useMemo(() => displayService.getStatistics(), [displayService])
  const displayExpensesByCategory = useMemo(() => displayService.getExpensesByCategory(), [displayService])
  const displaySpendingData = useMemo(() => displayService.getLast30DaysSpending(), [displayService])
  const budgetUtilization = useMemo(() => displayService.getBudgetUtilization(), [displayService])

  const [syncedChartHeight, setSyncedChartHeight] = useState<number | null>(null)

  const applySync = (h: number) => {
    setSyncedChartHeight((prev) => {
      if (!prev) return h
      // keep the larger height so charts don't clip
      return Math.max(prev, h)
    })
  }

  const statItems = [
    {
      icon: TrendingDown,
      label: 'Total Monthly Expenses',
      value: formatCurrency(displayStats.totalExpenses),
      color: 'red',
      subtext: `Includes ${formatCurrency(displayStats.totalEMI)} in loan EMI`,
    },
    { icon: Wallet, label: 'Total Budget Limit', value: formatCurrency(displayStats.totalBudgets), color: 'blue' },
    { icon: Target, label: 'Active Goals', value: displayStats.activeGoals, color: 'green' },
    { icon: Zap, label: 'Active Loans', value: displayStats.activeLoans, color: 'yellow' },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <motion.div className="fluid-grid mb-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        {statItems.map((item, index) => (
          <StatCard key={index} title={item.label} value={item.value} icon={item.icon} className="min-h-[6rem]" />
        ))}
      </motion.div>

      {(financialProfile?.monthly_salary || 0) > 0 && (
        <motion.div className="mb-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <MonthlySavingsTracker
            monthlyIncome={parseFloat(String(financialProfile?.monthly_salary || 0))}
            totalEMI={displayStats.totalEMI}
            totalBudget={displayStats.budgetAmount}
            currency={currency}
            isLoading={false}
          />
        </motion.div>
      )}

      <motion.div className="mb-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <FluidGrid min="420px" className="mb-0">
          <Card className="flex flex-col h-full p-4" aria-label="Expense Distribution">
            <div className="flex-1 min-h-0" style={{ minHeight: 'var(--chart-min-height)', height: syncedChartHeight ? syncedChartHeight : undefined }}>
              <ChartGuard sync={applySync} className="h-full">
                <ExpenseDistributionChart data={displayExpensesByCategory} />
              </ChartGuard>
            </div>
          </Card>

          <Card className="flex flex-col h-full p-4" aria-label="Spending Trend">
            <div className="flex-1" style={{ minHeight: 'var(--chart-min-height)', height: syncedChartHeight ? syncedChartHeight : undefined }}>
              <ChartGuard sync={applySync} className="h-full">
                <SpendingTrendChart data={displaySpendingData} viewType="30days" />
              </ChartGuard>
            </div>
          </Card>
        </FluidGrid>
      </motion.div>

      <motion.div className="mb-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }}>
        <FluidGrid min="240px">
          <Card
            className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/30 dark:to-blue-800/30 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate('/expenses')}
          >
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Recent Transactions</p>
                <p className="font-bold text-blue-600 dark:text-blue-400 mt-1" style={{ fontSize: 'calc(var(--font-base) * 1.6)' }}>{expenses.length}</p>
              </div>
              <div className="text-blue-400"><TrendingDown /></div>
            </div>
          </Card>

          <Card
            className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/30 dark:to-green-800/30 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate('/goals')}
          >
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Goals in Progress</p>
                <p className="font-bold text-green-600 dark:text-green-400 mt-1" style={{ fontSize: 'calc(var(--font-base) * 1.6)' }}>{displayStats.activeGoals}</p>
              </div>
              <div className="text-green-400"><Target /></div>
            </div>
          </Card>

          <Card
            className="bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/30 dark:to-yellow-800/30 cursor-pointer hover:shadow-lg transition-shadow"
            onClick={() => navigate('/budgets')}
          >
            <div className="flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-sm-fluid text-gray-600 dark:text-gray-400">Budgets Setup</p>
                <p className="font-bold text-yellow-600 dark:text-yellow-400 mt-1" style={{ fontSize: 'calc(var(--font-base) * 1.6)' }}>{budgets.length}</p>
              </div>
              <div className="text-yellow-400"><Wallet /></div>
            </div>
          </Card>
        </FluidGrid>
      </motion.div>

      {/* Budget Utilization Grid */}
      <motion.div className="mb-8" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h3 className="text-lg font-semibold mb-4 dark:text-gray-100">Budget Utilization (Current Month)</h3>
        <FluidGrid min="240px">
          {budgetUtilization.map((b) => (
            <Card key={b.id} className="p-3">
              <div className="flex items-center justify-between">
                <div className="min-w-0">
                  <p className="text-sm-fluid text-gray-600 dark:text-gray-400 capitalize">{b.name}</p>
                  <p className="font-bold text-gray-900 dark:text-white mt-1">{formatCurrency(b.spent)}</p>
                  <p className="text-xs-fluid text-gray-500 dark:text-gray-400">{b.percentage}% used</p>
                </div>
                <div className="w-20"><BudgetUtilizationChart data={[b]} /></div>
              </div>
              <div className="mt-3">
                <ProgressBar value={b.percentage} max={100} color={b.isOverBudget ? 'bg-red-500' : 'bg-primary-600'} />
              </div>
            </Card>
          ))}
        </FluidGrid>
      </motion.div>
    </motion.div>
  )
}
