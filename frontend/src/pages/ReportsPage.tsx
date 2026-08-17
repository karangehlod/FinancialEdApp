/**
 * ReportsPage — spending analytics with charts and data export.
 *
 * Responsibilities (SRP):
 *  - Guard route via useProtectedRoute
 *  - Derive monthly trends and category breakdown from expense/budget/goal stores
 *  - Delegate chart rendering to Recharts
 *  - Export data via exportService
 */

import React, { useEffect, useRef, useMemo, useCallback, type ChangeEvent } from 'react'
import { useState } from 'react'
import { motion } from 'framer-motion'
import { BarChart2, Download, TrendingUp } from 'lucide-react'
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

import { Layout, PageContainer } from '@/components/Layout'
import { Button, Select, LoadingSpinner, FluidIcon } from '@/components/UI'
import { FluidGrid } from '@/components/FluidGrid'
import { useProtectedRoute } from '@/hooks/useAuth'
import { useCurrency } from '@/hooks/useCurrency'
import { useExpenseStore, useBudgetStore, useGoalStore } from '@/store/index'
import { showSuccessToast, showErrorToast } from '@/utils/toast'
import { exportService } from '@/services/exportService'

// ── Constants ──────────────────────────────────────────────────────────────

const CHART_COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316']

const MONTHS_SHORT = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

const CATEGORY_LABELS: Record<string, string> = {
  food: 'Food', transport: 'Transport', utilities: 'Utilities',
  entertainment: 'Entertainment', health: 'Health', education: 'Education',
  shopping: 'Shopping', other: 'Other',
}

const TIME_RANGE_OPTIONS = [
  { value: '3', label: 'Last 3 Months' },
  { value: '6', label: 'Last 6 Months' },
  { value: '12', label: 'Last 12 Months' },
]

// ── Sub-components ─────────────────────────────────────────────────────────

interface StatTileProps {
  label: string
  value: string
  colorClass: string
}

const StatTile: React.FC<StatTileProps> = ({ label, value, colorClass }) => (
  <div className={`glass rounded-lg p-4 border-l-4 ${colorClass}`}>
    <p className="text-xs-fluid text-gray-500 dark:text-gray-400 mb-1">{label}</p>
    <p className={`text-lg font-bold ${colorClass.replace('border-', 'text-')}`}>{value}</p>
  </div>
)

// ── Main component ─────────────────────────────────────────────────────────

export const ReportsPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useProtectedRoute()
  const { formatCurrency } = useCurrency()
  const dataFetchedRef = useRef(false)

  const { expenses, fetchExpenses, isLoading: expLoading } = useExpenseStore()
  const { budgets, fetchBudgets } = useBudgetStore()
  const { goals, fetchGoals } = useGoalStore()

  const [timeRange, setTimeRange] = useState('6')

  useEffect(() => {
    if (isAuthenticated && !dataFetchedRef.current) {
      dataFetchedRef.current = true
      fetchExpenses().catch(console.error)
      fetchBudgets().catch(console.error)
      fetchGoals().catch(console.error)
    }
  }, [isAuthenticated, fetchExpenses, fetchBudgets, fetchGoals])

  // ── Derived data ───────────────────────────────────────────────────────

  const rangeMonths = parseInt(timeRange, 10)

  const recentExpenses = useMemo(() => {
    const cutoff = new Date()
    cutoff.setMonth(cutoff.getMonth() - rangeMonths)
    return expenses.filter((e) => new Date(e.date) >= cutoff)
  }, [expenses, rangeMonths])

  // Monthly spending trend
  const monthlyTrend = useMemo(() => {
    const map: Record<string, number> = {}
    const now = new Date()
    for (let i = rangeMonths - 1; i >= 0; i--) {
      const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
      const key = `${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`
      map[key] = 0
    }
    for (const e of recentExpenses) {
      const d = new Date(e.date)
      const key = `${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`
      if (key in map) map[key] = (map[key] ?? 0) + (parseFloat(String(e.amount)) || 0)
    }
    return Object.entries(map).map(([month, amount]) => ({ month, amount: parseFloat(amount.toFixed(2)) }))
  }, [recentExpenses, rangeMonths])

  // Category breakdown
  const categoryBreakdown = useMemo(() => {
    const map: Record<string, number> = {}
    for (const e of recentExpenses) {
      const cat = e.category ?? 'other'
      map[cat] = (map[cat] ?? 0) + (parseFloat(String(e.amount)) || 0)
    }
    return Object.entries(map)
      .sort(([, a], [, b]) => b - a)
      .map(([category, amount], i) => ({
        category,
        label: CATEGORY_LABELS[category] ?? category,
        amount: parseFloat(amount.toFixed(2)),
        color: CHART_COLORS[i % CHART_COLORS.length] ?? CHART_COLORS[0],
      }))
  }, [recentExpenses])

  // Budget vs actual for current month
  const budgetVsActual = useMemo(() => {
    const now = new Date()
    const month = now.getMonth() + 1
    const year = now.getFullYear()
    const monthBudgets = budgets.filter(
      (b) => (b as { month: number }).month === month && (b as { year: number }).year === year
    )
    return monthBudgets.map((b) => ({
      category: CATEGORY_LABELS[b.category] ?? b.category,
      budget: (b as { allocated_amount?: number }).allocated_amount ?? b.amount ?? 0,
      spent: (b as { spent_amount?: number }).spent_amount ?? b.spent ?? 0,
    }))
  }, [budgets])

  // Stats
  const stats = useMemo(() => {
    const total = recentExpenses.reduce((s, e) => s + (parseFloat(String(e.amount)) || 0), 0)
    const avg = monthlyTrend.length > 0 ? total / monthlyTrend.length : 0
    const topCategory = categoryBreakdown[0]
    const activeGoals = goals.filter((g) => g.status === 'active').length
    const completedGoals = goals.filter((g) => g.status === 'completed').length
    return { total, avg, topCategory, activeGoals, completedGoals }
  }, [recentExpenses, monthlyTrend, categoryBreakdown, goals])

  // ── Export handlers ────────────────────────────────────────────────────

  const handleExportCSV = useCallback(() => {
    try {
      exportService.exportExpensesCSV(
        expenses.map((e) => ({ ...e })),
        `expenses_${new Date().toISOString().split('T')[0]}`,
      )
      showSuccessToast('CSV exported')
    } catch {
      showErrorToast('Export failed')
    }
  }, [expenses])

  const handleExportJSON = useCallback(() => {
    try {
      exportService.exportToJSON(
        `expenses_${new Date().toISOString().split('T')[0]}`,
        expenses.map((e) => ({ ...e })),
      )
      showSuccessToast('JSON exported')
    } catch {
      showErrorToast('Export failed')
    }
  }, [expenses])

  // ── Guard ──────────────────────────────────────────────────────────────

  if (!isAuthenticated || isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
          <LoadingSpinner size="lg" />
        </div>
      </Layout>
    )
  }

  if (expLoading) {
    return (
      <Layout>
        <PageContainer title="Reports" subtitle="Analytics and insights" icon={BarChart2}>
          <div className="flex items-center justify-center" style={{ minHeight: 'var(--placeholder-height)' }}>
            <LoadingSpinner size="lg" />
          </div>
        </PageContainer>
      </Layout>
    )
  }

  return (
    <Layout>
      <PageContainer title="Reports" subtitle="Analytics and insights" icon={BarChart2}>

        {/* Controls */}
        <motion.div className="flex flex-wrap gap-4 items-end justify-between mb-6"
          initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="w-52">
            <Select label="Time Range" options={TIME_RANGE_OPTIONS} value={timeRange}
              onChange={(e: ChangeEvent<HTMLSelectElement>) => setTimeRange(e.target.value)} />
          </div>
          <div className="flex gap-2">
            <Button variant="secondary" className="gap-2" onClick={handleExportCSV}>
              <FluidIcon icon={Download} size="sm" />
              Export CSV
            </Button>
            <Button variant="secondary" className="gap-2" onClick={handleExportJSON}>
              <FluidIcon icon={Download} size="sm" />
              Export JSON
            </Button>
          </div>
        </motion.div>

        {/* Stat tiles */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mb-6">
          <FluidGrid min="160px" className="gap-4">
            <StatTile label={`Total Spent (${rangeMonths}m)`} value={formatCurrency(stats.total)} colorClass="border-red-500" />
            <StatTile label="Monthly Average" value={formatCurrency(stats.avg)} colorClass="border-blue-500" />
            <StatTile label="Top Category" value={stats.topCategory ? CATEGORY_LABELS[stats.topCategory.category] ?? stats.topCategory.category : '—'} colorClass="border-yellow-500" />
            <StatTile label="Active Goals" value={`${stats.activeGoals} (${stats.completedGoals} done)`} colorClass="border-green-500" />
          </FluidGrid>
        </motion.div>

        {/* Monthly Trend */}
        <motion.div className="glass rounded-lg p-4 sm:p-6 mb-6"
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="flex items-center gap-2 mb-4">
            <FluidIcon icon={TrendingUp} size="sm" className="text-blue-500" />
            <h2 className="font-semibold text-gray-900 dark:text-gray-100">Monthly Spending Trend</h2>
          </div>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={monthlyTrend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
              <Tooltip formatter={(v: number) => [formatCurrency(v), 'Spent']} />
              <Line type="monotone" dataKey="amount" stroke="#3B82F6" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </motion.div>

        <FluidGrid min="300px" className="gap-6 mb-6">

          {/* Category Breakdown */}
          <motion.div className="glass rounded-lg p-4 sm:p-6"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">Spending by Category</h2>
            {categoryBreakdown.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-sm-fluid text-center py-8">No data in this period</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={categoryBreakdown} dataKey="amount" nameKey="label" cx="50%" cy="50%"
                    outerRadius={80} label={({ label, percent }) => `${label} ${((percent ?? 0) * 100).toFixed(0)}%`}
                    labelLine={false}>
                    {categoryBreakdown.map((entry, i) => (
                      <Cell key={`cell-${i}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => [formatCurrency(v), 'Amount']} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </motion.div>

          {/* Budget vs Actual */}
          <motion.div className="glass rounded-lg p-4 sm:p-6"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">Budget vs Actual (This Month)</h2>
            {budgetVsActual.length === 0 ? (
              <p className="text-gray-500 dark:text-gray-400 text-sm-fluid text-center py-8">No budgets set for this month</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={budgetVsActual} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                  <XAxis dataKey="category" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v: number) => `$${v}`} />
                  <Tooltip formatter={(v: number) => [formatCurrency(v)]} />
                  <Legend />
                  <Bar dataKey="budget" fill="#3B82F6" name="Budget" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="spent" fill="#EF4444" name="Spent" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </motion.div>
        </FluidGrid>

        {/* Category breakdown table */}
        {categoryBreakdown.length > 0 && (
          <motion.div className="glass rounded-lg p-4 sm:p-6"
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
            <h2 className="font-semibold text-gray-900 dark:text-gray-100 mb-4">Category Breakdown</h2>
            <div className="space-y-2">
              {categoryBreakdown.map((entry) => (
                <div key={entry.category} className="flex items-center gap-3">
                  <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: entry.color }} />
                  <span className="flex-1 text-sm-fluid text-gray-700 dark:text-gray-300">{entry.label}</span>
                  <span className="font-medium text-sm-fluid">{formatCurrency(entry.amount)}</span>
                  <span className="text-xs-fluid text-gray-500 dark:text-gray-400 w-12 text-right">
                    {stats.total > 0 ? ((entry.amount / stats.total) * 100).toFixed(0) : 0}%
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </PageContainer>
    </Layout>
  )
}
